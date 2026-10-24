from pressready import access


def _reset(monkeypatch, product=""):
    monkeypatch.setenv("PRESSREADY_FREE_PER_DAY", "2")
    monkeypatch.setenv("PRESSREADY_GUMROAD_PRODUCT_ID", product)
    access._free_counts.clear()
    access._key_cache.clear()


def test_free_tier_counts_per_client(monkeypatch):
    _reset(monkeypatch)
    assert access.check(None, "a")[0] and access.check(None, "a")[0]
    ok, code, msg = access.check(None, "a")
    assert not ok and code == "free_limit" and "2 builds per day" in msg
    assert access.check(None, "b")[0]  # another client still has its own quota


def test_key_rejected_when_not_on_sale(monkeypatch):
    _reset(monkeypatch)
    ok, code, msg = access.check("KEY", "a")
    assert not ok and code == "invalid_key" and "not on sale" in msg


def test_valid_and_refunded_keys(monkeypatch):
    _reset(monkeypatch, product="prod123")
    answers = {"GOOD": {"success": True, "purchase": {}},
               "REFUNDED": {"success": True, "purchase": {"refunded": True}},
               "CANCELLED": {"success": True, "purchase": {"subscription_cancelled_at": "2026-10-01"}},
               "BAD": {"success": False}}
    calls = []

    class Resp:
        def __init__(self, body):
            self.body = body

        def read(self):
            import json
            return json.dumps(self.body).encode()

    def fake_urlopen(req, timeout=0):
        import urllib.parse
        key = urllib.parse.parse_qs(req.data.decode())["license_key"][0]
        calls.append(key)
        return Resp(answers[key])

    monkeypatch.setattr(access.urllib.request, "urlopen", fake_urlopen)
    assert access.check("GOOD", "a")[0]
    assert access.check("GOOD", "a")[0] and calls.count("GOOD") == 1  # cached
    assert access.check("REFUNDED", "a")[1] == "invalid_key"
    assert "no longer active" in access.check("CANCELLED", "a")[2]
    assert access.check("BAD", "a")[2] == "unknown license key"


def test_pricing_shows_paid_plan_only_when_configured(monkeypatch):
    _reset(monkeypatch)
    assert access.pricing()["status"] == "free_beta"
    _reset(monkeypatch, product="prod123")
    monkeypatch.setenv("PRESSREADY_BUY_URL", "https://example.com/buy")
    p = access.pricing()
    assert p["status"] == "live" and p["plans"][1]["buy_url"] == "https://example.com/buy"
