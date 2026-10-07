"""upload.py against a bucket and a Cloudflare API that live in memory."""
import hashlib
import io
import json

import pytest

import upload
from papers import FILES_URL

BITCOIN = FILES_URL + "crypto/bitcoin-A-ivory.pdf"


class Bucket:
    """The calls of the S3 API that upload.py makes, on a dict {key: bytes}."""

    def __init__(self):
        self.objects, self.puts = {}, []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        objects = self.objects

        class Paginator:
            def paginate(self, Bucket):
                yield {"Contents": [{"Key": k, "ETag": f'"{hashlib.md5(v).hexdigest()}"'}
                                    for k, v in sorted(objects.items())]}
        return Paginator()

    def put_object(self, Bucket, Key, Body, **kw):
        self.objects[Key] = Body
        self.puts.append(Key)

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        del self.objects[Key]


class Site:
    """dist/ and release/us/ in a temporary folder, a bucket, and the calls to Cloudflare."""

    def __init__(self, tmp_path, monkeypatch):
        self.dist, self.us = tmp_path / "dist", tmp_path / "release" / "us"
        for d in (self.dist, self.us):
            (d / "crypto").mkdir(parents=True)
        monkeypatch.setattr(upload, "DIST", self.dist)
        monkeypatch.setattr(upload, "US", self.us)
        self.bucket = Bucket()
        monkeypatch.setattr(upload, "client", lambda: self.bucket)
        monkeypatch.setenv("R2_ENDPOINT", "https://r2.invalid")  # a dry run reads the bucket too
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
        monkeypatch.setenv("CLOUDFLARE_ZONE_ID", "zone")
        monkeypatch.setattr(upload, "cloudflare", self.cloudflare)
        # the papers make every PDF of the test, but those named stale-*
        monkeypatch.setattr(upload, "expected_keys", lambda: {
            f"crypto/{f.name}" for d in (self.dist, self.us) for f in (d / "crypto").glob("*.pdf")
            if not f.name.startswith("stale-")})
        self.monkeypatch, self.calls, self.fail = monkeypatch, [], False

    def cloudflare(self, path, body=None):
        self.calls.append(body["files"])
        if self.fail and body["files"] != [FILES_URL]:  # the token passes its check, the purge fails
            raise SystemExit(f"error: the Cloudflare API call {path} failed")

    def write(self, name, data, us=False):
        ((self.us if us else self.dist) / "crypto" / name).write_bytes(data)

    def run(self, *args, fail=False):
        """Runs upload.py; returns the purge requests, each a list of URLs."""
        self.fail, self.calls[:], self.bucket.puts[:] = fail, [], []
        self.monkeypatch.setattr("sys.argv", ["upload.py", *args])
        try:
            upload.main()
        finally:
            checked = self.calls[:1] == [[FILES_URL]]  # the token, checked on the root of FILES_URL first
            purges = self.calls[1:] if checked else self.calls[:]
        return purges


@pytest.fixture
def site(tmp_path, monkeypatch):
    return Site(tmp_path, monkeypatch)


def test_new_files_are_uploaded_without_a_purge_and_changed_ones_are_purged(site):
    site.write("bitcoin-A-ivory.pdf", b"v1")
    site.write("bitcoin-letter-ivory.pdf", b"us v1", us=True)
    assert site.run() == []  # never served yet, so never in the cache of Cloudflare
    assert sorted(site.bucket.objects) == ["crypto/bitcoin-A-ivory.pdf", "crypto/bitcoin-letter-ivory.pdf"]
    site.write("bitcoin-A-ivory.pdf", b"v2")
    assert site.run() == [[BITCOIN]]
    assert site.bucket.puts == [upload.PENDING_KEY, "crypto/bitcoin-A-ivory.pdf"]
    assert site.bucket.objects["crypto/bitcoin-A-ivory.pdf"] == b"v2"
    assert upload.PENDING_KEY not in site.bucket.objects  # removed once the purge succeeded
    assert site.run() == [] and site.bucket.puts == []  # nothing changed


def test_a_file_of_the_bucket_that_dist_lacks_is_kept(site, capsys):
    site.bucket.objects["crypto/renamed-A-ivory.pdf"] = b"old"
    site.write("bitcoin-A-ivory.pdf", b"v1")
    site.run()
    assert "crypto/renamed-A-ivory.pdf" in site.bucket.objects
    assert "kept crypto/renamed-A-ivory.pdf" in capsys.readouterr().out


def test_a_pdf_that_no_paper_makes_is_not_uploaded(site, capsys):
    site.write("bitcoin-A-ivory.pdf", b"v1")
    site.write("stale-A-ivory.pdf", b"a renamed paper")
    site.run()
    assert list(site.bucket.objects) == ["crypto/bitcoin-A-ivory.pdf"]
    assert "not uploaded crypto/stale-A-ivory.pdf: no paper makes it any more" in capsys.readouterr().out


def test_the_papers_make_a_pdf_per_format_and_theme():
    keys = upload.expected_keys()
    assert "crypto/bitcoin-A-ivory.pdf" in keys and "crypto/bitcoin-letter-blueprint.pdf" in keys
    assert all(k.count("/") == 1 and k.endswith(".pdf") for k in keys)


def test_purges_go_in_batches(site):
    names = [f"p{i:02}-A-ivory.pdf" for i in range(upload.PURGE_BATCH + 1)]
    for n in names:
        site.write(n, b"v1")
    site.run()
    for n in names:
        site.write(n, b"v2")
    purges = site.run()
    assert [len(p) for p in purges] == [upload.PURGE_BATCH, 1]
    assert sorted(u for p in purges for u in p) == [FILES_URL + "crypto/" + n for n in names]


def test_a_purge_that_fails_is_done_by_the_next_run(site):
    site.write("bitcoin-A-ivory.pdf", b"v1")
    site.run()
    site.write("bitcoin-A-ivory.pdf", b"v2")
    with pytest.raises(SystemExit):
        site.run(fail=True)
    assert site.bucket.objects["crypto/bitcoin-A-ivory.pdf"] == b"v2"  # uploaded, but cached as v1
    assert json.loads(site.bucket.objects[upload.PENDING_KEY]) == [BITCOIN]
    # the next run finds the file unchanged, and purges it all the same
    assert site.run() == [[BITCOIN]]
    assert upload.PENDING_KEY not in site.bucket.objects


def test_a_run_without_a_cloudflare_token_leaves_its_purge_to_one_that_has_it(site, monkeypatch, capsys):
    site.write("bitcoin-A-ivory.pdf", b"v1")
    site.run()
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN")
    site.write("bitcoin-A-ivory.pdf", b"v2")
    assert site.run() == []
    assert json.loads(site.bucket.objects[upload.PENDING_KEY]) == [BITCOIN]
    assert "wait in purge-pending.json" in capsys.readouterr().out
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    assert site.run() == [[BITCOIN]]  # the file is unchanged since, and purged all the same
    assert upload.PENDING_KEY not in site.bucket.objects


def test_a_dry_run_writes_nothing(site, capsys):
    site.write("bitcoin-A-ivory.pdf", b"v1")
    site.run()
    site.write("bitcoin-A-ivory.pdf", b"v2")
    assert site.run("--dry-run") == []
    assert site.bucket.objects["crypto/bitcoin-A-ivory.pdf"] == b"v1" and site.bucket.puts == []
    out = capsys.readouterr().out
    assert "would upload crypto/bitcoin-A-ivory.pdf (changed)" in out
    assert "would purge 1 URL(s)" in out
