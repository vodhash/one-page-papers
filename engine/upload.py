#!/usr/bin/env python3
"""Uploads the PDFs of dist/ to the bucket served at FILES_URL, where the site and the README link
them: only the files that differ from the bucket, as <category>/<file>.

    python3 engine/upload.py              # upload what changed, then purge it from the Cloudflare cache
    python3 engine/upload.py --dry-run    # say what would be uploaded, without writing anything

The bucket is Cloudflare R2, through its S3 API, with the credentials of the environment:
R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_ENDPOINT (https://<account id>.r2.cloudflarestorage.com),
and R2_BUCKET (default onepagepapers-pdf). With CLOUDFLARE_API_TOKEN (Zone, Cache Purge) and
CLOUDFLARE_ZONE_ID as well, the files that changed are purged from the cache of Cloudflare, which
otherwise serves the old file until its cache runs out (a year, by the cache rule of the zone). A
file of the bucket that dist/ no longer has is reported, never deleted: a link to it may still be
around.

Needs boto3 (requirements-deploy.txt), which only the deployment installs.
"""
import argparse, hashlib, json, os, pathlib, sys, urllib.error, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from papers import FILES_URL, ROOT

DIST = ROOT / "dist"
BUCKET = "onepagepapers-pdf"
# a week: a file keeps its name when its poster changes, so its cache must run out. The cache rule
# of files.onepagepapers.com keeps it a year in the cache of Cloudflare instead, which the purge
# above empties; browsers keep the week, since a purge cannot reach them
CACHE_CONTROL = "public, max-age=604800, stale-while-revalidate=86400"
PURGE_BATCH = 30  # URLs per purge request, the most that every Cloudflare plan takes

def local_files():
    """{key in the bucket: path} of every PDF of dist/."""
    return {f.relative_to(DIST).as_posix(): f for f in sorted(DIST.glob("*/*.pdf"))}

def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()

def client():
    missing = [k for k in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT") if not os.environ.get(k)]
    if missing:
        sys.exit(f"error: {', '.join(missing)} missing from the environment")
    import boto3
    from botocore.config import Config
    # R2 takes the checksums that boto3 sends by default only when an operation requires one
    config = Config(region_name="auto", retries={"max_attempts": 5, "mode": "standard"},
                    request_checksum_calculation="when_required", response_checksum_validation="when_required")
    return boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"], config=config,
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])

def remote_files(s3, bucket):
    """{key: ETag} of the bucket. A file put in one request has the MD5 of its content as ETag."""
    out = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for o in page.get("Contents", []):
            out[o["Key"]] = o["ETag"].strip('"')
    return out

def cloudflare(path, body=None):
    """A call to the API of Cloudflare with CLOUDFLARE_API_TOKEN; fails unless it succeeds."""
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/{path}", method="POST" if body else "GET",
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ok = json.load(r).get("success")
    except urllib.error.HTTPError as e:
        ok = False
        print(f"Cloudflare API {path}: HTTP {e.code}", file=sys.stderr)
    if not ok:
        sys.exit(f"error: the Cloudflare API call {path} failed, check CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID")

def check_purge():
    """Fails at once on a token or zone that cannot purge, rather than on the day a PDF changes:
    purges the root of FILES_URL, which serves no file."""
    if os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ZONE_ID"):
        cloudflare(f"zones/{os.environ['CLOUDFLARE_ZONE_ID']}/purge_cache", {"files": [FILES_URL]})

def purge(urls):
    token, zone = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ZONE_ID")
    if not (token and zone):
        print(f"not purged from the Cloudflare cache (no CLOUDFLARE_API_TOKEN or CLOUDFLARE_ZONE_ID): "
              f"Cloudflare serves the old version of the {len(urls)} changed file(s) until its cache runs out")
        return
    for i in range(0, len(urls), PURGE_BATCH):
        cloudflare(f"zones/{zone}/purge_cache", {"files": urls[i:i + PURGE_BATCH]})
    print(f"purged {len(urls)} URL(s) from the Cloudflare cache")

def main():
    ap = argparse.ArgumentParser(description="Upload the PDFs of dist/ that changed to the bucket of FILES_URL.")
    ap.add_argument("--dry-run", action="store_true", help="say what would be uploaded, write nothing")
    a = ap.parse_args()
    files = local_files()
    if not files:
        sys.exit("error: dist/ holds no PDF, build them first (make)")
    bucket = os.environ.get("R2_BUCKET") or BUCKET
    if a.dry_run and not os.environ.get("R2_ENDPOINT"):
        s3, remote = None, {}
        print("no R2_ENDPOINT: comparing with an empty bucket")
    else:
        s3 = client()
        remote = remote_files(s3, bucket)
        if not a.dry_run:
            check_purge()
    changed = [k for k, f in files.items() if remote.get(k) != md5(f)]
    for k in changed:
        print(("would upload" if a.dry_run else "upload"), k, "(new)" if k not in remote else "(changed)")
        if not a.dry_run:
            s3.put_object(Bucket=bucket, Key=k, Body=files[k].read_bytes(), ContentType="application/pdf",
                          CacheControl=CACHE_CONTROL)
    for k in sorted(set(remote) - set(files)):
        print(f"kept {k}: in the bucket, not in dist/")
    print(f"{len(changed)} of {len(files)} PDF(s) {'to upload' if a.dry_run else 'uploaded'}, "
          f"{len(files) - len(changed)} unchanged")
    if not a.dry_run and (updated := [FILES_URL + k for k in changed if k in remote]):
        purge(updated)

if __name__ == "__main__":
    main()
