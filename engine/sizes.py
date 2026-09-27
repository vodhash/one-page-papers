#!/usr/bin/env python3
"""Keeps large files out of git: a binary file over MAX_BYTES, or a file of dist/, which the CI
builds and git does not keep, fails. The images of a paper (papers/<category>/<slug>/, the scans
its poster prints) may reach MAX_SOURCE_BYTES.

    python3 engine/sizes.py            # every file that git tracks (the CI)
    python3 engine/sizes.py --staged   # the files that the next commit adds or changes (.githooks/pre-commit)
"""
import argparse, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 5 * 1024 * 1024
SOURCE_IMAGE = re.compile(r"^papers/[^/]+/[^/]+/.+\.(?:png|jpe?g|webp|gif|tiff?)$", re.I)

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout

def problems(paths, read):
    """Messages for the paths that break the rules; read(path) gives the content of a file."""
    out = []
    for path in paths:
        if path.startswith("dist/"):
            out.append(f"{path}: dist/ is built by the CI, git does not keep it")
            continue
        data = read(path)
        if len(data) <= MAX_BYTES or b"\0" not in data[:8192]:
            continue
        if SOURCE_IMAGE.match(path):
            if len(data) > MAX_SOURCE_BYTES:
                out.append(f"{path}: {len(data) / 2**20:.1f} MiB, over the {MAX_SOURCE_BYTES // 2**20} MiB of an "
                           "image of a paper: reduce it to what the poster prints")
        else:
            out.append(f"{path}: a binary file of {len(data) / 2**20:.1f} MiB, over {MAX_BYTES // 2**20} MiB "
                       "outside the images of a paper")
    return out

def main():
    ap = argparse.ArgumentParser(description="Fail on a large binary file or a file of dist/ in git.")
    ap.add_argument("--staged", action="store_true", help="check the files that the next commit adds or changes")
    a = ap.parse_args()
    if a.staged:
        paths = git("diff", "--cached", "--name-only", "--diff-filter=AMR", "-z").decode().split("\0")
        found = problems([p for p in paths if p], lambda p: git("show", f":{p}"))
    else:
        paths = git("ls-files", "-z").decode().split("\0")
        found = problems([p for p in paths if p and (ROOT / p).is_file()], lambda p: (ROOT / p).read_bytes())
    if found:
        sys.exit("error: " + "\nerror: ".join(found))

if __name__ == "__main__":
    main()
