"""Client network resolution behind an explicitly trusted reverse proxy.

Forwarding headers are client-controlled unless a proxy we operate rewrites
them, so they are read only when the direct peer is a configured proxy, and
then from the right: the first hop that is not a trusted proxy is the client.
"""

import ipaddress
from collections.abc import Sequence
from typing import Literal, Protocol

Network = ipaddress.IPv4Network | ipaddress.IPv6Network
Address = ipaddress.IPv4Address | ipaddress.IPv6Address
ForwardedHeader = Literal["x-forwarded-for", "forwarded"]


class HeaderSource(Protocol):
    def getlist(self, key: str) -> list[str]: ...


def parse_trusted_proxies(value: str) -> tuple[Network, ...]:
    """Parse comma-separated addresses/CIDRs; raise ValueError on any bad entry."""
    return tuple(
        ipaddress.ip_network(item.strip(), strict=False)
        for item in value.split(",")
        if item.strip()
    )


def parse_address(value: str) -> Address | None:
    """Accept bare, quoted, bracketed and port-suffixed forms; None if invalid."""
    host = value.strip().strip('"')
    if host.startswith("["):
        host = host[1 : host.find("]")] if "]" in host else ""
    elif host.count(":") == 1:
        host = host.split(":", 1)[0]
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def forwarded_hops(headers: HeaderSource, header: ForwardedHeader) -> list[str]:
    values = ",".join(headers.getlist(header))
    if header == "x-forwarded-for":
        return [hop.strip() for hop in values.split(",") if hop.strip()]
    hops = []
    for element in values.split(","):
        for pair in element.split(";"):
            key, _, value = pair.strip().partition("=")
            if key.strip().lower() == "for" and value.strip():
                hops.append(value.strip())
    return hops


def client_address(
    peer: str,
    headers: HeaderSource,
    trusted: Sequence[Network],
    header: ForwardedHeader,
) -> str:
    """Return the client address; headers are ignored unless the peer is trusted."""

    def is_trusted(value: str) -> bool:
        address = parse_address(value)
        return address is not None and any(address in net for net in trusted)

    candidate = peer
    if not trusted or not is_trusted(candidate):
        return normalized(candidate)
    for hop in reversed(forwarded_hops(headers, header)):
        candidate = hop
        if not is_trusted(candidate):
            break
    return normalized(candidate)


def normalized(value: str) -> str:
    address = parse_address(value)
    return str(address) if address is not None else value.strip()
