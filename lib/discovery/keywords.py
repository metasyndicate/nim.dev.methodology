"""Keyword extraction from a free-text request: stopword-filtered unigrams + adjacent bigrams.

Deliberately simple and deterministic. The agent (or human) is expected to pass explicit
keywords with -k when it can do better; extraction is the fallback and is recorded as such.
"""

from __future__ import annotations

import re

from .util import singular

STOP = set(
    """
a about above across after again against all also am an and any are as at be because been before
being below between both but by can could did do does doing down during each either else etc
every few for from further get gets given had has have having he her here hers him his how i if
in into is it its itself just let like make makes many may me might more most much must my need
needs new no nor not now of off on once one only or other our ours out over own per please plus
rather really same shall she should so some such than that the their them then there these they
this those through to too toward under until up upon us use used uses using very via want wants
was we well were what when where which while who whom whose why will with within without would
yet you your build building create creating design designing develop developing implement
implementing support supporting manage managing handle handling track tracking provide providing
allow allowing able model modeling modelling data based project projects work thing things stuff
way ways kind lot lots idea ideas set sets system systems tool tools app application platform
service services simple basic
""".split()
)

# Keep a few domain-bearing words even though they're in STOP for generic text.
KEEP_IF_ALONE = {"data", "model", "system", "service", "application", "tool"}

TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]*")


def tokens(text: str) -> list[str]:
    out = []
    for t in TOKEN.findall(text or ""):
        t = re.sub(r"[^a-z0-9_-]", "", singular(t.lower().strip(".-")))
        if t:
            out.append(t)
    return out


def _content(toks: list[str]) -> list[str | None]:
    return [t if (t not in STOP and len(t) > 2) else None for t in toks]


def extract(text: str, limit: int = 20) -> list[str]:
    out: list[str] = []

    def add(k: str) -> None:
        if k and k not in out:
            out.append(k)

    # bigrams first: they carry the most specific meaning. They never span punctuation
    # ("orders, invoices" is a list, not a concept). A generic qualifier ("data lineage",
    # "service endpoint") may lead a bigram but not stand alone.
    segments = [
        tokens(s) for s in re.split(r"[,;:.!?()\[\]\n/&]+|\band\b|\bor\b", text or "")
    ]
    for toks in segments:
        content = _content(toks)
        for (ta, a), b in zip(zip(toks, content), content[1:]):
            if b and (a or ta in KEEP_IF_ALONE):
                add(f"{a or ta} {b}")
    for toks in segments:
        for t in _content(toks):
            if t:
                add(t)
    if not out:  # nothing but generic words: fall back to the kept generic ones
        for t in tokens(text):
            if t in KEEP_IF_ALONE:
                add(t)
    return out[:limit]


def parse_explicit(spec: list[str]) -> list[str]:
    """['a, b', 'c'] -> ['a', 'b', 'c'] normalized (lowercase, single-spaced, singular)."""
    out: list[str] = []
    for chunk in spec:
        for k in chunk.split(","):
            k = " ".join(singular(w) for w in re.findall(r"[a-z0-9_-]+", k.lower()))
            if k and k not in out:
                out.append(k)
    return out
