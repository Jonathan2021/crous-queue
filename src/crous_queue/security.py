import hmac
import ipaddress
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe

from itsdangerous import BadSignature, URLSafeTimedSerializer

from crous_queue.config import Settings
from crous_queue.network import client_address, parse_address, parse_trusted_proxies

__all__ = [
    "COOKIE",
    "Identity",
    "client_address",
    "coarse_ip_hash",
    "device_session",
    "parse_trusted_proxies",
]

COOKIE = "cq_device"


@dataclass(frozen=True)
class Identity:
    device_hash: str
    ip_hash: str


def device_session(settings: Settings, cookie: str | None) -> tuple[str, str, bool]:
    signer = URLSafeTimedSerializer(
        settings.session_secret, salt="crous-queue-device-v1"
    )
    try:
        token = signer.loads(cookie or "", max_age=30 * 24 * 3600)
        if not isinstance(token, str) or len(token) < 32:
            raise BadSignature("Invalid token")
        valid = True
    except BadSignature:
        token, valid = token_urlsafe(32), False
    device = hmac.new(
        settings.session_secret.encode(), token.encode(), sha256
    ).hexdigest()
    return device, signer.dumps(token), valid


def coarse_ip_hash(settings: Settings, ip: str, day: str) -> str:
    address = parse_address(ip)
    if address is None:
        value = "local-unknown"
    else:
        value = str(
            ipaddress.ip_network(
                f"{address}/{24 if address.version == 4 else 56}", strict=False
            )
        )
    return hmac.new(
        settings.ip_secret.encode(), f"{day}:{value}".encode(), sha256
    ).hexdigest()
