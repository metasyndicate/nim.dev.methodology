"""Shared primitives: time, hashing, text normalization, cached HTTP (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0"
USER_AGENT = f"nim.discovery/{VERSION} (ontology discovery; stdlib urllib)"


class OfflineMiss(RuntimeError):
    """Raised in --offline mode when a URL is not in the cache."""


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def load_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def dump_json(obj, p: Path) -> None:
    Path(p).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# -- text ---------------------------------------------------------------------

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("sses", "xes", "ches", "shes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is", "ys")):
        return w[:-1]
    return w


def norm(text: str) -> str:
    """'CustomerOrders' / 'customer_orders' / 'Customer orders' -> 'customer order'."""
    t = _CAMEL.sub(" ", text or "")
    words = re.findall(r"[a-z0-9]+", t.lower())
    return " ".join(singular(w) for w in words)


def pascal(text: str) -> str:
    return "".join(
        w[:1].upper() + w[1:]
        for w in re.findall(r"[A-Za-z0-9]+", _CAMEL.sub(" ", text))
    )


def camel(text: str) -> str:
    p = pascal(text)
    return p[:1].lower() + p[1:]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60] or "bundle"


def first(v):
    """First item of a list-or-scalar JSON-LD value."""
    if isinstance(v, list):
        return v[0] if v else None
    return v


def as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def text_of(v) -> str | None:
    """JSON-LD literal (str | {'@value'} | list) -> str."""
    v = first(v)
    if isinstance(v, dict):
        v = v.get("@value")
    return v if isinstance(v, str) else None


# -- cached HTTP --------------------------------------------------------------


def cache_dir() -> Path:
    base = os.environ.get("NIM_DISCOVERY_CACHE") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
        "nim",
        "discovery",
    )
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


class Fetcher:
    """GET with an on-disk cache keyed by URL hash. Records provenance of every URL used."""

    def __init__(self, offline: bool = False, refresh: bool = False, timeout: int = 30):
        self.offline, self.refresh, self.timeout = offline, refresh, timeout
        self.log: dict[str, dict] = {}

    def get(self, url: str, ttl_days: float = 7) -> bytes:
        key = sha256_bytes(url.encode())
        body, meta = cache_dir() / f"{key}.body", cache_dir() / f"{key}.json"
        fresh = (
            body.exists() and (time.time() - body.stat().st_mtime) < ttl_days * 86400
        )
        if body.exists() and (self.offline or (fresh and not self.refresh)):
            data = body.read_bytes()
            m = load_json(meta) if meta.exists() else {"retrieved": None}
            self._record(url, m.get("retrieved") or now(), data, cached=True)
            return data
        if self.offline:
            raise OfflineMiss(url)
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = r.read()
                break
            except (urllib.error.URLError, TimeoutError) as e:  # transient; back off
                last = e
                time.sleep(1.5 * (attempt + 1))
        else:
            if body.exists():  # stale cache beats failure; recorded as cached
                data = body.read_bytes()
                self._record(
                    url,
                    load_json(meta).get("retrieved") if meta.exists() else now(),
                    data,
                    cached=True,
                )
                return data
            raise last  # type: ignore[misc]
        body.write_bytes(data)
        stamp = now()
        dump_json({"url": url, "retrieved": stamp}, meta)
        self._record(url, stamp, data, cached=False)
        return data

    def json(self, url: str, ttl_days: float = 7):
        return json.loads(self.get(url, ttl_days).decode("utf-8"))

    def _record(self, url, retrieved, data, cached):
        self.log[url] = {
            "url": url,
            "retrieved": retrieved,
            "sha256": sha256_bytes(data),
            "cached": cached,
        }
