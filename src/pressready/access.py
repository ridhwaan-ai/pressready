"""Access control: a small free tier per client, unlimited builds with a paid Gumroad license key.

Configuration (environment variables on the server):
- PRESSREADY_FREE_PER_DAY: free builds per client per UTC day without a key (default 3).
- PRESSREADY_GUMROAD_PRODUCT_ID: the Gumroad product whose license keys unlock unlimited builds.
  Unset = paid keys are not on sale yet (the free tier still works).
- PRESSREADY_BUY_URL: where agents/people buy a key (shown in errors and /v1/pricing).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

GUMROAD_VERIFY = "https://api.gumroad.com/v2/licenses/verify"
CACHE_SECONDS = 3600

_free_counts: dict[tuple[str, str], int] = {}
_key_cache: dict[str, tuple[float, bool, str]] = {}


def free_per_day() -> int:
    return int(os.environ.get("PRESSREADY_FREE_PER_DAY", "3"))


def product_id() -> str:
    return os.environ.get("PRESSREADY_GUMROAD_PRODUCT_ID", "").strip()


def buy_url() -> str:
    return os.environ.get("PRESSREADY_BUY_URL", "").strip()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def verify_key(key: str) -> tuple[bool, str]:
    """(valid, reason). Valid = a real, unrefunded purchase with an active subscription (if it is one)."""
    hit = _key_cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1], hit[2]
    if not product_id():
        return False, "paid keys are not on sale yet; use the free tier"
    data = urllib.parse.urlencode({"product_id": product_id(), "license_key": key,
                                   "increment_uses_count": "false"}).encode()
    try:
        out = json.load(urllib.request.urlopen(urllib.request.Request(GUMROAD_VERIFY, data=data), timeout=20))
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}") if e.code == 404 else {"success": False, "message": f"HTTP {e.code}"}
    except Exception as e:  # Gumroad unreachable: don't cache, let the caller retry
        return False, f"could not reach the license server ({type(e).__name__}); retry shortly"
    p = out.get("purchase") or {}
    if not out.get("success"):
        ok, why = False, "unknown license key"
    elif p.get("refunded") or p.get("chargebacked") or p.get("disputed"):
        ok, why = False, "this license was refunded or disputed"
    elif p.get("subscription_ended_at") or p.get("subscription_cancelled_at") or p.get("subscription_failed_at"):
        ok, why = False, "this subscription is no longer active"
    else:
        ok, why = True, "ok"
    _key_cache[key] = (time.time(), ok, why)
    return ok, why


def check(key: str | None, client: str) -> tuple[bool, str, str]:
    """(allowed, error_code, message). Call once per build; it counts free builds."""
    if key:
        ok, why = verify_key(key)
        return (True, "", "") if ok else (False, "invalid_key", why)
    day = _today()
    for k in [k for k in _free_counts if k[1] != day]:
        _free_counts.pop(k)
    used = _free_counts.get((client, day), 0)
    if used >= free_per_day():
        more = f" Buy a key at {buy_url()} and send it as 'Authorization: Bearer <key>'." if buy_url() else ""
        return False, "free_limit", f"free tier is {free_per_day()} builds per day per client and it is used up.{more}"
    _free_counts[(client, day)] = used + 1
    return True, "", ""


def pricing() -> dict:
    plans = [{"name": "free", "price_usd": 0, "builds_per_day": free_per_day(), "key_required": False}]
    if product_id():
        plans.append({"name": "unlimited", "key_required": True, "buy_url": buy_url(),
                      "how_to_use": "send the license key as 'Authorization: Bearer <key>'",
                      "price": "see buy_url"})
    return {"currency": "USD", "status": "live" if product_id() else "free_beta", "plans": plans}
