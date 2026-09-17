"""Same slug function as data/build_wiki.py, so page anchors and index anchors always agree."""
import re
import unicodedata


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")
