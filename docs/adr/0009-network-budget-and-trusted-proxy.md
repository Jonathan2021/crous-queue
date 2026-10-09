# ADR-0009 — per-network counting budget and trusted proxy

Accepted for the private MVP, 2026-10-09 (Foundry work `92380c5c`, package P3).

## Context

The 2026-10-09 portfolio review reproduced cookie churn: six fresh cookies from one
script posted six 120-minute estimates for RU Cuvier and `/venues/paris:r177/waits`
returned `state: recent, minutes: 120, count: 6`. We reproduced it again on a scratch
copy of the development database before changing code
(`docs/evidence/p3-20261009/sybil-repro-before.txt`). Devices are free, so "count"
read like six people. Separately, the client address came from the TCP peer only:
behind the reverse proxy proposed for a hosted beta every user would share one
network bucket (one 120/hour ceiling for the whole site), while trusting
`X-Forwarded-For` blindly would let any client pick its own bucket.

## Decision

1. **Count budget, not rejection.** Each report stores the request's coarse network
   key (keyed, daily-rotating hash of IPv4 /24 or IPv6 /56, the key the rate limiter
   already used). Aggregation keeps the latest visible fresh estimate per device as
   before, then counts at most `CQ_NETWORK_ESTIMATE_CAP` (default 2, range 1–10) of
   the newest per network. Writes from a shared network still succeed; excess ones
   are retained but not counted. The same budget applies to meal/seat observations.
2. **Honest semantics.** The wait state exposes `count` (counted devices), `sources`
   (distinct networks among them) and `excluded` (fresh estimates left out). The UI
   says "2 appareils · 1 seul réseau · 1 autre du même réseau non compté" rather than
   "N signalements". Estimates carry a per-response ordinal `source` label (`s1`…),
   never a hash.
3. **Trusted proxy, default none.** `CQ_TRUSTED_PROXIES` lists proxy addresses/CIDRs
   (empty by default). Only when the TCP peer is listed is the single header chosen
   by `CQ_FORWARDED_HEADER` (`x-forwarded-for` default, or RFC 7239 `forwarded`)
   read, from the right; the first hop that is not a trusted proxy is the client.
   The other header is never read, so a proxy that passes it through cannot be used
   to spoof. Invalid configuration fails at startup. Uvicorn proxy headers stay off.
4. **NAT tolerance.** The hard network ceiling becomes `CQ_NETWORK_HOURLY_LIMIT`
   (default 120 per action per hour). Because counting is already capped, the
   ceiling only guards storage and can be raised for a campus without weakening the
   consensus defence.
5. **Moderation.** `/admin` shows an 8-character opaque network label per report and
   `POST /admin/reports/{id}/hide-network` hides every visible report from that
   network bucket received in the last two hours, one versioned audit row each.
6. **Retention.** The retention job clears `network_hash` on reports older than 24
   hours, keeping the existing "rate identifiers ≤ 24 h" promise.

## Alternatives considered

- *Minimum device age before a report counts* (review suggestion). Not adopted: the
  primary pilot path is a student opening the app for the first time while in the
  queue, and a script can pre-mint cookies and wait. It delays honest first reports
  without bounding a prepared attacker.
- *Device fingerprinting / accounts.* Rejected by ADR-0001 privacy boundaries.
- *Exact-IP grouping instead of /24.* Fewer honest collisions on carrier pools, but
  a host with several neighbouring addresses escapes trivially. Kept /24 and /56 to
  match the existing limiter; revisit with field data.

## Consequences

- This limits repeats and bursts from one network, **not identities**. An attacker
  with addresses in several /24s (VPNs, mobile data, IPv6 prefixes) still gets
  `cap` counted estimates per network. One device alone can still set the value of
  an otherwise empty venue; the UI labels it "non confirmé".
- Honest students behind one campus NAT (eduroam) or the same carrier /24 count at
  most `cap` at a time; their writes are kept and shown as "non compté(s)".
- Around 00:00 UTC the daily key rotates, so one network can briefly count twice.
- A misconfigured trusted proxy list (for example trusting `0.0.0.0/0`) re-opens
  spoofing; deployment documents must state the exact proxy address.

## Revisit when

Real pilot data shows honest same-network contributors routinely excluded, an
attacker uses many networks, or a hosted deployment changes the proxy topology.
