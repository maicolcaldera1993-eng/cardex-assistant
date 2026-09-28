"""Section anchors: the knowledge-base builders (data/build_wiki.py, data/build_manuals.py) and the app share this
one function, so page anchors and index anchors always agree."""
import re
import unicodedata


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")
