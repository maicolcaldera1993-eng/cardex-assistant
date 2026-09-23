"""Meaning, not words: maps what a person says, in any language, onto a node of the
knowledge base.

A small multilingual sentence-embedding model (paraphrase-multilingual-MiniLM-L12-v2,
118M parameters, runs on CPU in ~10 ms per sentence, no network) turns a sentence into a
vector. Sentences with the same meaning land close together, whatever the language.

Two rules keep this safe in a spare-parts domain:
  * similarity only CHOOSES AMONG candidates the graph already allows (the sections of the
    machine being discussed). It never fetches a document on its own.
  * below a threshold nothing is proposed: small talk is not a symptom.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

INDEX = Path(__file__).resolve().parents[2] / "data" / "kb" / "index.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SYMPTOM_THRESHOLD = 0.66     # measured: small talk 0.27-0.44, generic "there is a problem" up to 0.69 (decoy), real faults 0.67-0.92
SECTION_THRESHOLD = 0.64
AMBIGUITY_GAP = 0.04         # two symptoms this close: show both, the operator picks
DECOY_MARGIN = 0.03          # a symptom must beat the generic decoy by this much, not just edge past it


@dataclass
class Match:
    node_id: str
    score: float
    ref: str


class SemanticIndex:
    def __init__(self, index_path: Path = INDEX, model_name: str = MODEL_NAME):
        self.nodes: dict[str, dict] = {n["id"]: n for n in json.loads(index_path.read_text(encoding="utf-8"))}
        self._model_name = model_name
        self._model = None
        self._vecs: np.ndarray | None = None
        self._owners: list[str] = []
        self._refs: list[str] = []

    @property
    def ready(self) -> bool:
        return self._vecs is not None

    def load(self) -> None:
        """Loads the model and embeds every reference text once (a few seconds at start-up)."""
        from fastembed import TextEmbedding
        self._model = TextEmbedding(self._model_name)
        for nid, n in self.nodes.items():
            for ref in n["refs"]:
                self._owners.append(nid)
                self._refs.append(ref)
        self._vecs = self._embed(self._refs)

    def _embed(self, texts: list[str]) -> np.ndarray:
        v = np.array(list(self._model.embed(texts)), dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    def search(self, text: str, allowed: set[str] | None = None, kind: str | None = None, k: int = 2) -> list[Match]:
        """Best nodes for `text`, one entry per node, restricted to `allowed` ids and/or a kind."""
        if not self.ready or (len(text.split()) < 2 and len(text.strip()) < 6):
            return []
        q = self._embed([text])[0]
        sims = self._vecs @ q
        best: dict[str, tuple[float, str]] = {}
        for owner, ref, s in zip(self._owners, self._refs, sims):
            if allowed is not None and owner not in allowed:
                continue
            if kind and self.nodes[owner]["kind"] != kind:
                continue
            if owner not in best or s > best[owner][0]:
                best[owner] = (float(s), ref)
        ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[:k]
        return [Match(nid, round(s, 3), ref) for nid, (s, ref) in ranked]

    def similarities(self, text: str, sentences: list[str]) -> list[float]:
        """Cosine similarity of `text` with each sentence (0.0 everywhere when the model is not loaded)."""
        if not self.ready or not sentences:
            return [0.0] * len(sentences)
        v = self._embed(sentences) @ self._embed([text])[0]
        return [float(x) for x in v]

    def best_sentence(self, text: str, sentences: list[str]) -> tuple[str, float] | None:
        """The sentence of a section that says the same thing as `text` (to highlight it)."""
        if not self.ready or not sentences:
            return None
        v = self._embed(sentences) @ self._embed([text])[0]
        i = int(np.argmax(v))
        return sentences[i], float(v[i])

    def ids_for(self, kind: str, model_id: str | None = None, family_models: list[str] | None = None) -> set[str]:
        """Graph filter: the nodes of one kind that belong to the machine (or family) being discussed."""
        models = {model_id} if model_id else set(family_models or [])
        return {nid for nid, n in self.nodes.items()
                if n["kind"] == kind and (not models or models & set(n["models"]))}
