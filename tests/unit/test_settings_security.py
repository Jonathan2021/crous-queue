import os
import stat

import pytest

from crous_queue.config import Settings, load_settings
from crous_queue.configuration import configure
from crous_queue.security import coarse_ip_hash, device_session

SECRETS = dict(session_secret="s" * 40, ip_secret="i" * 40)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """No developer .env or exported CQ_* value may leak into these checks."""
    monkeypatch.chdir(tmp_path)
    for key in [k for k in os.environ if k.startswith("CQ_")]:
        monkeypatch.delenv(key)


def settings(**overrides):
    values = dict(environment="test", database_url="sqlite:///test-x.db", **SECRETS)
    return Settings(**{**values, **overrides})


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (dict(session_secret="short"), "32\\+ character"),
        (dict(ip_secret="s" * 40), "must differ"),
        (dict(admin_token="i" * 40), "must differ"),
        (dict(database_url="mysql://db/test"), "sqlite:/// or postgresql"),
        (dict(database_url="sqlite:///crous.db"), "unmarked database"),
        (dict(environment="demo", database_url="sqlite:///test.db"), "named demo"),
        (dict(environment="production"), "Production requires PostgreSQL"),
        (
            dict(
                environment="production",
                database_url="postgresql+psycopg://app@db/crous",
                origin="https://crous.example",
                secure_cookies=True,
                admin_token="short",
            ),
            "separate random admin token",
        ),
    ],
)
def test_unsafe_configuration_is_refused(overrides, message):
    with pytest.raises(ValueError, match=message):
        settings(**overrides)


def test_production_requires_and_accepts_only_the_full_safe_profile():
    production = settings(
        environment="production",
        database_url="postgresql+psycopg://app@db/crous",
        origin="https://crous.example",
        secure_cookies=True,
        admin_token="a" * 40,
    )
    assert production.environment == "production" and production.secure_cookies


def test_profile_errors_never_echo_secret_values(tmp_path):
    profile = tmp_path / "custom.env"
    profile.write_text(
        "CQ_ENVIRONMENT=test\nCQ_DATABASE_URL=sqlite:///test.db\n"
        "CQ_SESSION_SECRET=leaky-secret-value\nCQ_IP_SECRET=leaky-secret-value\n"
    )
    with pytest.raises(ValueError, match="Invalid Crous Queue configuration") as error:
        load_settings(profile)
    assert "leaky-secret-value" not in str(error.value)
    profile.write_text(
        "CQ_ENVIRONMENT=test\nCQ_DATABASE_URL=sqlite:///test.db\n"
        f"CQ_SESSION_SECRET={'s' * 40}\nCQ_IP_SECRET={'i' * 40}\nCQ_PORT=8123\n"
    )
    assert load_settings(profile).port == 8123


def test_generated_profiles_are_private_separate_and_never_replaced(tmp_path):
    development = configure()
    demo = configure(demo=True)
    assert development.resolve() == (tmp_path / ".env").resolve()
    assert demo.resolve() == (tmp_path / ".local/demo.env").resolve()
    for path in [development, demo]:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / ".local").stat().st_mode) == 0o700
    original = development.read_bytes()
    assert configure() == development and development.read_bytes() == original
    dev, dem = load_settings(development), load_settings(demo)
    assert (dev.environment, dem.environment) == ("development", "demo")
    assert dem.port == 8001 and dem.origin == "http://127.0.0.1:8001"
    assert {dev.session_secret, dev.ip_secret, dev.admin_token}.isdisjoint(
        {dem.session_secret, dem.ip_secret, dem.admin_token}
    )
    assert len({dev.session_secret, dev.ip_secret, dev.admin_token}) == 3


def test_device_cookie_round_trip_and_forgery():
    current = settings()
    device, cookie, valid = device_session(current, None)
    assert not valid and cookie
    again, reissued, valid = device_session(current, cookie)
    assert valid and again == device and reissued
    assert device_session(current, cookie + "x")[2] is False
    other = settings(session_secret="o" * 40)
    stranger, _, valid = device_session(other, cookie)
    assert not valid and stranger != device


def test_network_hash_is_coarse_daily_and_tolerates_unknown_addresses():
    current = settings()
    same_v4 = {
        coarse_ip_hash(current, ip, "2026-10-07")
        for ip in ["203.0.113.7", "203.0.113.250"]
    }
    assert len(same_v4) == 1
    assert coarse_ip_hash(current, "203.0.114.7", "2026-10-07") not in same_v4
    assert coarse_ip_hash(current, "203.0.113.7", "2026-10-08") not in same_v4
    v6 = [
        coarse_ip_hash(current, ip, "2026-10-07")
        for ip in ["2001:db8:abcd:12::1", "2001:db8:abcd:ff::9", "2001:db8:abcd:112::1"]
    ]
    assert v6[0] == v6[1] != v6[2]  # one /56 prefix per bucket
    unknown = coarse_ip_hash(current, "testclient", "2026-10-07")
    assert unknown == coarse_ip_hash(current, "", "2026-10-07")
