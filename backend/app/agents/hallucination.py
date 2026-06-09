from __future__ import annotations

import re
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import get_settings


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


@lru_cache(maxsize=1)
def load_nli_model() -> CrossEncoder:
    return CrossEncoder(get_settings().nli_model)


def _lexical_entailment(sentence: str, context: str) -> float:
    sentence_terms = set(re.findall(r"[a-zA-Z0-9]+", sentence.lower()))
    context_terms = set(re.findall(r"[a-zA-Z0-9]+", context.lower()))
    if not sentence_terms:
        return 1.0
    return len(sentence_terms & context_terms) / len(sentence_terms)


def score_hallucination(
    answer: str,
    context: str,
    model: CrossEncoder | None = None,
    load_model: bool = True,
) -> float:
    sentences = split_sentences(answer)
    if not sentences:
        return 0.0
    entailment_scores = []
    try:
        if not load_model and model is None:
            raise RuntimeError("NLI model disabled")
        nli = model or load_nli_model()
        raw_scores = nli.predict([(context, sentence) for sentence in sentences])
        for raw in raw_scores:
            if hasattr(raw, "__len__"):
                entailment_scores.append(float(max(raw)))
            else:
                entailment_scores.append(float(raw))
    except Exception:
        entailment_scores = [_lexical_entailment(sentence, context) for sentence in sentences]
    unsupported = [score for score in entailment_scores if score < 0.5]
    return len(unsupported) / len(sentences)
