"""
@author:     Sid Probstein
@contact:    sid@swirl.today
"""

import os
import re
from functools import lru_cache
from typing import Dict

import numpy as np
import spacy

try:
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)

try:
    from django.conf import settings
    _DEFAULT_LANG = getattr(settings, "SWIRL_DEFAULT_LANGUAGE", "en")
    _SWIRL_SPACY_USE_EMBEDDINGS_CACHE = getattr(settings, "SWIRL_SPACY_USE_EMBEDDINGS_CACHE", True)
    _SWIRL_SPACY_EMBEDDINGS_CACHE_MAXSIZE = getattr(settings, "SWIRL_SPACY_EMBEDDINGS_CACHE_MAXSIZE", 2000)
except Exception:
    _DEFAULT_LANG = "en"
    _SWIRL_SPACY_USE_EMBEDDINGS_CACHE = True
    _SWIRL_SPACY_EMBEDDINGS_CACHE_MAXSIZE = 2000

_MODEL_MAP = {
    "en": os.getenv("SWIRL_SPACY_MODEL_EN", "en_core_web_lg"),
    "en_sm": "en_core_web_sm",
}

_MIN_NORM: float = 1e-12
_UNIT_ATOL: float = 1e-3
_EPS32: float = np.finfo(np.float32).eps

_nlp_cache: Dict[str, spacy.language.Language] = {}


def _load_pipeline(lang: str) -> spacy.language.Language:
    model_name = _MODEL_MAP.get(lang)
    if model_name is None:
        raise ValueError(f"Unsupported language code '{lang}'")
    try:
        ret = spacy.load(model_name)
        logger.info(f"Loaded spaCy model '{model_name}'")
        return ret
    except OSError as e:
        raise RuntimeError(
            f"spaCy model '{model_name}' not installed. "
            f"Install with:\n  python -m spacy download {model_name}"
        ) from e


def get_spacy_nlp(lang: str | None = None, size: str | None = None) -> spacy.language.Language:
    """Return the (singleton) spaCy pipeline for lang (default: en)."""
    lang = (lang or _DEFAULT_LANG).lower()
    if size:
        lang = f"{lang}_{size}"
    if lang not in _nlp_cache:
        _nlp_cache[lang] = _load_pipeline(lang)
    return _nlp_cache[lang]


_ws_re = re.compile(r'\s+')


def _normalize_text(s: str) -> str:
    return _ws_re.sub(' ', s.strip())


def to_unit_fp16(x) -> np.ndarray:
    if x is None:
        out = np.zeros((0,), dtype=np.float16, order="C")
        out.setflags(write=False)
        return out
    v = np.asarray(x, dtype=np.float32, order="C")
    if v.ndim != 1 or v.size == 0 or not np.all(np.isfinite(v)):
        out = np.zeros((v.size,), dtype=np.float16, order="C")
        out.setflags(write=False)
        return out
    n = float(np.linalg.norm(v))
    if n < _MIN_NORM:
        out = np.zeros_like(v, dtype=np.float16, order="C")
        out.setflags(write=False)
        return out
    u32 = v / n
    u16 = u32.astype(np.float16, copy=False, order="C")
    n2 = float(np.linalg.norm(u16.astype(np.float32, copy=False)))
    if abs(1.0 - n2) > _UNIT_ATOL:
        u32 = (u16.astype(np.float32, copy=False)) / max(n2, _EPS32)
        u16 = u32.astype(np.float16, copy=False, order="C")
    u16.setflags(write=False)
    return u16


@lru_cache(maxsize=_SWIRL_SPACY_EMBEDDINGS_CACHE_MAXSIZE)
def _cached_sentence_vector(lang: str, normalized_text: str) -> np.ndarray:
    nlp = get_spacy_nlp(lang)
    doc = nlp.make_doc(normalized_text)
    return to_unit_fp16(doc.vector)


def get_sentence_vector(text: str, lang: str | None = None) -> np.ndarray:
    if _SWIRL_SPACY_USE_EMBEDDINGS_CACHE:
        lang = (lang or _DEFAULT_LANG).lower()
        return _cached_sentence_vector(lang, _normalize_text(text))
    nlp = get_spacy_nlp(lang)
    doc = nlp(text)
    return doc.vector


# Legacy: module-level nlp kept for any code that imports it directly.
try:
    nlp = get_spacy_nlp()
except Exception:
    nlp = None
