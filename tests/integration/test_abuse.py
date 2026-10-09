"""P3 abuse model: cookie churn, network budgets and trusted proxies.

These limit repeats and bursts from one network, not identities. Clients are
given explicit documentation-range peer addresses (RFC 5737) so network
grouping is deliberate rather than an accident of the test transport.
"""

from datetime import timedelta
from uuid import uuid4

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from crous_queue.app import create_app
from crous_queue.db import make_engine
from crous_queue.distribution import directory_snapshot, migration_configuration
from crous_queue.models import ModerationAudit, WaitReport
from crous_queue.services.directory import DirectoryImporter
from crous_queue.services.maintenance import purge
from crous_queue.services.waits import WaitService
from tests.conftest import ADMIN, HEADERS, NOW
from tests.integration.test_reports import report

CUVIER = "/venues/paris:r177/waits"


def configured(application, **overrides):
    app, current = application
    settings = app.state.settings.model_copy(update=overrides)
    return create_app(settings, engine=app.state.engine, clock=lambda: current[0])


def fresh_device(app, address, *, headers=None):
    client = TestClient(app, client=(address, 40000), headers=headers or {})
    client.get("/health")
    return client


def test_six_fresh_cookies_from_one_network_cannot_fake_consensus(application):
    app, current = application
    clients = [fresh_device(app, "203.0.113.7") for _ in range(6)]
    # Shared NAT must not lock anyone out: every write is accepted and retained.
    assert [report(c, current, 120).status_code for c in clients] == [201] * 6
    state = clients[0].get(CUVIER).json()
    assert state["count"] == 2  # default configured cap per network and window
    assert state["sources"] == 1 and state["excluded"] == 4
    assert len(state["estimates"]) == 2
    assert {e["source"] for e in state["estimates"]} == {"s1"}
    # Two honest devices on other networks now face the burst as a conflict,
    # not as a 6-report consensus.
    for address in ["198.51.100.10", "192.0.2.20"]:
        assert report(fresh_device(app, address), current, 10).status_code == 201
    state = clients[0].get(CUVIER).json()
    assert (state["count"], state["sources"], state["excluded"]) == (4, 3, 4)
    assert state["state"] == "conflicting" and state["range"] == [10, 120]
    for c in clients:
        c.close()


def test_network_cap_is_configurable_and_distinct_networks_all_count(application):
    _, current = application
    strict = configured(application, network_estimate_cap=1)
    for _ in range(3):
        assert (
            report(fresh_device(strict, "203.0.113.7"), current, 30).status_code == 201
        )
    state = fresh_device(strict, "203.0.113.8").get(CUVIER).json()
    assert (state["state"], state["count"], state["excluded"]) == ("single", 1, 2)
    for address in ["198.51.100.1", "192.0.2.1", "2001:db8:1::5"]:
        assert report(fresh_device(strict, address), current, 30).status_code == 201
    state = fresh_device(strict, "203.0.113.8").get(CUVIER).json()
    assert (state["count"], state["sources"]) == (4, 4)


def test_admin_bulk_hide_by_network_bucket_frees_its_budget(application):
    app, current = application
    honest = fresh_device(app, "198.51.100.10")
    assert report(honest, current, 10).status_code == 201
    current[0] += timedelta(seconds=30)
    burst = [fresh_device(app, "203.0.113.99") for _ in range(3)]
    ids = [report(c, current, 120).json()["report"]["id"] for c in burst]
    state = honest.get(CUVIER).json()
    assert (state["count"], state["excluded"], state["state"]) == (3, 1, "conflicting")
    listed = honest.get("/admin/reports", headers=ADMIN).json()["items"]
    labels = {item["id"]: item["network_label"] for item in listed}
    assert len({labels[i] for i in ids}) == 1 and all(labels[i] for i in ids)
    assert len(set(labels.values())) == 2
    assert "network_hash" not in str(listed) and "device_hash" not in str(listed)
    payload = {"rationale": "Rafale de faux signalements"}
    assert (
        honest.post(
            f"/admin/reports/{ids[0]}/hide-network", headers=HEADERS, json=payload
        ).status_code
        == 401
    )
    hidden = honest.post(
        f"/admin/reports/{ids[0]}/hide-network", headers=ADMIN, json=payload
    )
    assert hidden.status_code == 200 and hidden.json()["hidden"] == 3
    again = honest.post(
        f"/admin/reports/{ids[0]}/hide-network", headers=ADMIN, json=payload
    )
    assert again.json()["hidden"] == 0
    state = honest.get(CUVIER).json()
    assert (state["state"], state["minutes"], state["count"]) == ("single", 10, 1)
    # A later device in the same /24 (for example shared campus NAT) counts again.
    assert report(fresh_device(app, "203.0.113.5"), current, 12).status_code == 201
    assert honest.get(CUVIER).json()["count"] == 2
    with Session(app.state.engine) as db:
        actions = db.scalars(select(ModerationAudit.action)).all()
        assert actions.count("hide_network") == 3


def test_hourly_network_ceiling_is_configurable(application):
    _, current = application
    tight = configured(application, network_hourly_limit=10)
    codes = [
        report(fresh_device(tight, "203.0.113.7"), current, 5).status_code
        for _ in range(11)
    ]
    assert codes == [201] * 10 + [429]
    # Another network is unaffected by that bucket.
    assert report(fresh_device(tight, "198.51.100.1"), current, 5).status_code == 201


def test_forwarded_headers_are_ignored_by_default(application):
    app, current = application
    # Default trusts no proxy: a client cannot escape its bucket by spoofing.
    for index in range(4):
        spoofed = {
            "X-Forwarded-For": f"198.51.{index}.1",
            "Forwarded": f"for=192.0.{index}.9",
        }
        client = fresh_device(app, "127.0.0.1", headers=spoofed)
        assert report(client, current, 40).status_code == 201
    state = client.get(CUVIER).json()
    assert (state["count"], state["sources"], state["excluded"]) == (2, 1, 2)


def test_trusted_proxy_restores_distinct_client_networks(application):
    _, current = application
    proxied = configured(application, trusted_proxies="127.0.0.1, ::1")
    for index in range(4):
        # A client-supplied prefix is ignored: the proxy appends the real peer.
        chain = {"X-Forwarded-For": f"203.0.113.250, 198.51.{index}.1"}
        client = fresh_device(proxied, "127.0.0.1", headers=chain)
        assert report(client, current, 40).status_code == 201
    state = client.get(CUVIER).json()
    assert (state["count"], state["sources"], state["excluded"]) == (4, 4, 0)
    # The same headers from an untrusted peer are ignored.
    for index in range(3):
        chain = {"X-Forwarded-For": f"192.0.{index}.1"}
        client = fresh_device(proxied, "203.0.113.5", headers=chain)
        assert report(client, current, 40, venue="paris:r175").status_code == 201
    state = client.get("/venues/paris:r175/waits").json()
    assert (state["count"], state["sources"]) == (2, 1)


def test_rfc7239_forwarded_header_when_selected(application):
    _, current = application
    proxied = configured(
        application, trusted_proxies="127.0.0.0/8", forwarded_header="forwarded"
    )
    for value in [
        'for="[2001:db8:a::1]:4711";proto=https',
        "for=198.51.100.17:4711",
        "for=192.0.2.60;proto=http;by=203.0.113.43",
    ]:
        client = fresh_device(proxied, "127.0.0.1", headers={"Forwarded": value})
        assert report(client, current, 25).status_code == 201
    state = client.get(CUVIER).json()
    assert (state["count"], state["sources"]) == (3, 3)


def test_network_identifier_is_dropped_within_24_hours(application, engine):
    app, current = application
    client = fresh_device(app, "203.0.113.7")
    assert report(client, current, 5, key=str(uuid4())).status_code == 201
    purge(engine, current[0] + timedelta(hours=23))
    with Session(engine) as db:
        assert db.scalar(select(WaitReport.network_hash)) is not None
    purge(engine, current[0] + timedelta(hours=24))
    with Session(engine) as db:
        stored = db.scalars(select(WaitReport)).all()
        assert len(stored) == 1 and stored[0].network_hash is None


def test_0007_upgrade_keeps_legacy_reports_as_separate_sources(tmp_path):
    url = f"sqlite:///{tmp_path / 'test-0006.db'}"
    with migration_configuration(url) as config:
        command.upgrade(config, "0006")
    engine = make_engine(url)
    with directory_snapshot() as path:
        DirectoryImporter(engine, lambda: NOW).import_snapshot(path)
    with engine.begin() as db:
        for device in ["a", "b", "c"]:
            db.execute(
                text(
                    "INSERT INTO wait_reports (id, venue_id, queue_kind, kind, minutes,"
                    " observed_at, received_at, device_hash, idempotency_key,"
                    " payload_digest, visibility, moderation_version, comment,"
                    " comment_status) VALUES (:id, 'paris:r177', 'student',"
                    " 'estimate', 10, :now, :now, :device, :key, :digest,"
                    " 'visible', 0, '', 'none')"
                ),
                dict(
                    id=str(uuid4()),
                    now=NOW.replace(tzinfo=None).isoformat(" "),
                    device=device * 64,
                    key="legacy-" + device * 8,
                    digest="f" * 64,
                ),
            )
    with migration_configuration(url) as config:
        command.upgrade(config, "head")
        state = WaitService(engine, lambda: NOW).state("paris:r177")
        assert (state.count, state.sources, state.excluded) == (3, 3, 0)
        command.downgrade(config, "0006")
        command.upgrade(config, "head")
    engine.dispose()
