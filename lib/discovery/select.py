"""Ontology selection: greedy weighted set cover of keywords by ontologies.

Gain of an ontology = sum over keywords of how much it improves the best score already
covered by the selection. Pins go first; excludes never enter. Stops at max_ontologies or
when the best remaining gain falls below MIN_GAIN.
"""

from __future__ import annotations

MIN_GAIN = 0.5
METHOD = f"greedy weighted set cover (score = match x rank decay x prior; min gain {MIN_GAIN})"


def select(candidates: list[dict], request: dict, priors) -> dict:
    keywords = request["keywords"]
    pins = list(request.get("pin") or [])
    excl = set(request.get("exclude") or [])
    cap = int(request.get("max_ontologies") or 5)

    best: dict[str, dict[str, float]] = {}
    exact: dict[str, set[str]] = {}
    covers: dict[str, set[str]] = {}
    for c in candidates:
        # text-only hits (synonym/definition matches) are evidence for humans, not for selection
        if c["kind"] == "schema" or c["ontology"] in excl or c["match"] == "text":
            continue
        o, k = c["ontology"], c["keyword"]
        if c["score"] > best.setdefault(o, {}).get(k, 0.0):
            best[o][k] = c["score"]
        if c["match"] in ("exact", "label"):
            covers.setdefault(o, set()).add(k)
        if c["match"] == "exact":
            exact.setdefault(o, set()).add(k)

    current = {k: 0.0 for k in keywords}
    chosen: list[dict] = []

    def take(o: str, gain: float, pinned: bool) -> None:
        for k, s in best.get(o, {}).items():
            current[k] = max(current.get(k, 0.0), s)
        cov, ex = sorted(covers.get(o, ())), sorted(exact.get(o, ()))
        why = f"covers {len(cov)}/{len(keywords)} keywords ({len(ex)} exact); prior {priors(o)}"
        chosen.append(
            {
                "id": o,
                "selected": True,
                "pinned": pinned,
                "prior": priors(o),
                "score": round(gain, 4),
                "covers": cov,
                "exact": ex,
                "reason": ("pinned; " if pinned else "") + why,
            }
        )

    for o in pins:
        if o not in excl:
            take(o, sum(best.get(o, {}).values()), True)

    while len(chosen) < cap:
        taken = {c["id"] for c in chosen}
        gains = {
            o: sum(max(0.0, s - current.get(k, 0.0)) for k, s in ks.items())
            for o, ks in best.items()
            if o not in taken
        }
        if not gains:
            break
        o, g = max(
            gains.items(), key=lambda kv: (kv[1], len(exact.get(kv[0], ())), kv[0])
        )
        if g < MIN_GAIN:
            break
        take(o, g, False)

    taken = {c["id"] for c in chosen}
    runners = sorted(
        ((o, sum(ks.values())) for o, ks in best.items() if o not in taken),
        key=lambda kv: -kv[1],
    )[:8]
    for o, total in runners:
        cov, ex = sorted(covers.get(o, ())), sorted(exact.get(o, ()))
        chosen.append(
            {
                "id": o,
                "selected": False,
                "pinned": False,
                "prior": priors(o),
                "score": round(total, 4),
                "covers": cov,
                "exact": ex,
                "reason": f"not selected: marginal gain below {MIN_GAIN} or cap {cap} reached",
            }
        )

    covered = (
        set().union(*(set(c["covers"]) for c in chosen if c["selected"]))
        if chosen
        else set()
    )
    schemas = sorted(
        (c for c in candidates if c["kind"] == "schema" and c["match"] != "text"),
        key=lambda c: -c["score"],
    )[:8]
    return {
        "method": METHOD,
        "ontologies": chosen,
        "schemas": schemas,
        "uncovered": [k for k in keywords if k not in covered],
    }
