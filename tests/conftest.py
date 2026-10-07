"""The tests of the scripts of engine/ (build, markdown, upload, the site): they import them as the
scripts import each other, from engine/. The tests of the onepage_engine package are in
engine/tests/."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "engine"))
