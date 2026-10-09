import pytest
from starlette.datastructures import Headers

from crous_queue.config import Settings
from crous_queue.security import client_address, parse_trusted_proxies

LOCAL = parse_trusted_proxies("127.0.0.1, 10.0.0.0/8, ::1")


def headers(**values: str) -> Headers:
    return Headers({k.replace("_", "-"): v for k, v in values.items()})


@pytest.mark.parametrize(
    ("peer", "values", "trusted", "expected"),
    [
        ("127.0.0.1", {"x_forwarded_for": "198.51.100.1"}, (), "127.0.0.1"),
        ("203.0.113.9", {"x_forwarded_for": "198.51.100.1"}, LOCAL, "203.0.113.9"),
        ("127.0.0.1", {"x_forwarded_for": "198.51.100.1"}, LOCAL, "198.51.100.1"),
        (
            "127.0.0.1",
            {"x_forwarded_for": "6.6.6.6, 198.51.100.1, 10.1.2.3"},
            LOCAL,
            "198.51.100.1",
        ),
        ("127.0.0.1", {"x_forwarded_for": "10.0.0.5, 10.0.0.6"}, LOCAL, "10.0.0.5"),
        ("127.0.0.1", {"x_forwarded_for": "garbage"}, LOCAL, "garbage"),
        ("127.0.0.1", {}, LOCAL, "127.0.0.1"),
        ("::1", {"x_forwarded_for": "[2001:db8::7]:443"}, LOCAL, "2001:db8::7"),
        ("127.0.0.1", {"x_forwarded_for": "198.51.100.1:5000"}, LOCAL, "198.51.100.1"),
        ("::ffff:127.0.0.1", {"x_forwarded_for": "192.0.2.4"}, LOCAL, "192.0.2.4"),
    ],
)
def test_rightmost_untrusted_x_forwarded_for(peer, values, trusted, expected):
    assert (
        client_address(peer, headers(**values), trusted, "x-forwarded-for") == expected
    )


def test_selected_header_only():
    both = headers(x_forwarded_for="198.51.100.1", forwarded="for=192.0.2.1")
    assert client_address("127.0.0.1", both, LOCAL, "forwarded") == "192.0.2.1"
    assert client_address("127.0.0.1", both, LOCAL, "x-forwarded-for") == "198.51.100.1"
    multi = headers(forwarded='for=6.6.6.6, for="[2001:db8::1]";proto=https')
    assert client_address("127.0.0.1", multi, LOCAL, "forwarded") == "2001:db8::1"


def test_invalid_trusted_proxy_configuration_is_rejected():
    with pytest.raises(ValueError):
        parse_trusted_proxies("127.0.0.1, not-a-network")
    secrets = dict(session_secret="x" * 40, ip_secret="y" * 40)
    with pytest.raises(ValueError, match="CQ_TRUSTED_PROXIES"):
        Settings(
            environment="test",
            database_url="sqlite:///test.db",
            trusted_proxies="nope",
            **secrets,
        )
    with pytest.raises(ValueError):
        Settings(
            environment="test",
            database_url="sqlite:///test.db",
            network_estimate_cap=0,
            **secrets,
        )
    default = Settings(environment="test", database_url="sqlite:///test.db", **secrets)
    assert default.trusted_proxies == "" and default.network_estimate_cap == 2
    assert default.forwarded_header == "x-forwarded-for"
