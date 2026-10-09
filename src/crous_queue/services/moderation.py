from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from crous_queue.contracts import (
    CommentModerationInput,
    FlagInput,
    HideInput,
    NetworkHideInput,
    ReportView,
)
from crous_queue.models import ModerationAudit, ReportFlag, WaitReport
from crous_queue.security import Identity
from crous_queue.services.directory import plain_text
from crous_queue.services.waits import (
    DEFAULT_NETWORK_HOURLY_LIMIT,
    DomainError,
    aggregate,
    lock_writes,
    rate_limit,
)

BULK_HIDE_WINDOW = timedelta(hours=2)


class ModerationService:
    def __init__(
        self,
        engine: Engine,
        clock: Callable[[], datetime],
        *,
        network_limit: int = DEFAULT_NETWORK_HOURLY_LIMIT,
    ) -> None:
        self.engine, self.clock, self.network_limit = engine, clock, network_limit

    def flag(
        self, identity: Identity, report_id: str, payload: FlagInput
    ) -> dict[str, str]:
        with Session(self.engine) as db, db.begin():
            lock_writes(db, identity)
            report = db.get(WaitReport, report_id)
            if report is None:
                raise DomainError(404, "report_not_found", "Signalement introuvable.")
            previous = db.scalar(
                select(ReportFlag).where(
                    ReportFlag.report_id == report_id,
                    ReportFlag.device_hash == identity.device_hash,
                )
            )
            if previous:
                return {"id": previous.id, "status": "recorded"}
            rate_limit(
                db, identity, self.clock(), "flag", network_limit=self.network_limit
            )
            flag = ReportFlag(
                id=str(uuid4()),
                report_id=report_id,
                device_hash=identity.device_hash,
                reason=payload.reason,
                received_at=self.clock(),
            )
            db.add(flag)
            return {"id": flag.id, "status": "recorded"}

    def hide(self, report_id: str, payload: HideInput) -> dict[str, object]:
        with Session(self.engine) as db, db.begin():
            report = db.get(WaitReport, report_id, with_for_update=True)
            if report is None:
                raise DomainError(404, "report_not_found", "Signalement introuvable.")
            if report.moderation_version != payload.expected_version:
                raise DomainError(
                    409,
                    "moderation_conflict",
                    "Le signalement a changé. Actualisez avant de modérer.",
                )
            rationale = plain_text(payload.rationale)
            if len(rationale) < 8:
                raise DomainError(
                    422,
                    "rationale_required",
                    "Expliquez le motif de modération (8 caractères minimum).",
                )
            if report.visibility != "hidden":
                report.visibility = "hidden"
                report.moderation_version += 1
                db.add(
                    ModerationAudit(
                        id=str(uuid4()),
                        report_id=report.id,
                        action="hide",
                        rationale=rationale,
                        created_at=self.clock(),
                        version=report.moderation_version,
                    )
                )
            return dict(
                id=report.id,
                visibility=report.visibility,
                version=report.moderation_version,
            )

    def hide_network(self, report_id: str, payload: NetworkHideInput) -> dict[str, int]:
        """Hide every visible report sharing this report's network bucket.

        Scope: received within BULK_HIDE_WINDOW of now, all venues. The bucket is a
        coarse /24 or /56 on one UTC day, so shared NAT neighbours are included;
        each hidden report gets its own versioned audit row.
        """
        now = self.clock()
        with Session(self.engine) as db, db.begin():
            anchor = db.get(WaitReport, report_id)
            if anchor is None:
                raise DomainError(404, "report_not_found", "Signalement introuvable.")
            if not anchor.network_hash:
                raise DomainError(
                    422,
                    "network_unavailable",
                    "Réseau inconnu ou effacé après 24 h : masquez ce signalement seul.",
                )
            rationale = plain_text(payload.rationale)
            if len(rationale) < 8:
                raise DomainError(
                    422,
                    "rationale_required",
                    "Expliquez le motif de modération (8 caractères minimum).",
                )
            reports = db.scalars(
                select(WaitReport)
                .where(
                    WaitReport.network_hash == anchor.network_hash,
                    WaitReport.visibility == "visible",
                    WaitReport.received_at > now - BULK_HIDE_WINDOW,
                )
                .with_for_update()
            ).all()
            for report in reports:
                report.visibility = "hidden"
                report.moderation_version += 1
                db.add(
                    ModerationAudit(
                        id=str(uuid4()),
                        report_id=report.id,
                        action="hide_network",
                        rationale=rationale,
                        created_at=now,
                        version=report.moderation_version,
                    )
                )
            return {"hidden": len(reports)}

    def moderate_comment(
        self, report_id: str, payload: CommentModerationInput
    ) -> dict[str, object]:
        with Session(self.engine) as db, db.begin():
            report = db.get(WaitReport, report_id, with_for_update=True)
            if report is None:
                raise DomainError(404, "report_not_found", "Signalement introuvable.")
            if report.moderation_version != payload.expected_version:
                raise DomainError(
                    409, "moderation_conflict", "Le signalement a changé. Actualisez."
                )
            rationale = plain_text(payload.rationale)
            if (
                len(rationale) < 8
                or not report.comment
                or (report.visibility == "hidden" and payload.action != "delete")
            ):
                raise DomainError(
                    422,
                    "comment_unavailable",
                    "Commentaire absent, supprimé ou signalement masqué ; vérifiez le motif.",
                )
            report.comment_status = {
                "approve": "approved",
                "hide": "hidden",
                "delete": "deleted",
            }[payload.action]
            if payload.action == "delete":
                report.comment = ""
            report.moderation_version += 1
            db.add(
                ModerationAudit(
                    id=str(uuid4()),
                    report_id=report.id,
                    action="comment_" + payload.action,
                    rationale=rationale,
                    created_at=self.clock(),
                    version=report.moderation_version,
                )
            )
            return dict(
                id=report.id,
                comment_status=report.comment_status,
                version=report.moderation_version,
            )

    def list_reports(self, offset: int = 0) -> dict[str, object]:
        with Session(self.engine) as db:
            reports = db.scalars(
                select(WaitReport)
                .order_by(WaitReport.received_at.desc(), WaitReport.id)
                .offset(offset)
                .limit(51)
            ).all()
            items = []
            for report in reports[:50]:
                flags = (
                    db.scalar(
                        select(func.count())
                        .select_from(ReportFlag)
                        .where(ReportFlag.report_id == report.id)
                    )
                    or 0
                )
                audits = db.scalars(
                    select(ModerationAudit)
                    .where(ModerationAudit.report_id == report.id)
                    .order_by(ModerationAudit.created_at)
                ).all()
                items.append(
                    {
                        **ReportView.model_validate(report).model_dump(mode="json"),
                        "visibility": report.visibility,
                        "comment": report.comment,
                        "availability": {
                            name: getattr(report, name)
                            for name in ("grill", "vegetarian", "standard", "seating")
                        },
                        "version": report.moderation_version,
                        # Opaque grouping label for one day's coarse network bucket.
                        "network_label": (report.network_hash or "")[:8] or None,
                        "flag_count": flags,
                        "history": [
                            dict(
                                action=a.action,
                                rationale=a.rationale,
                                created_at=a.created_at,
                                version=a.version,
                            )
                            for a in audits
                        ],
                    }
                )
            return {
                "items": items,
                "next_offset": offset + 50 if len(reports) > 50 else None,
            }

    def metrics(self, *, venue_ids: Sequence[str] | None = None) -> dict[str, object]:
        now = self.clock()
        scope = [WaitReport.venue_id.in_(venue_ids)] if venue_ids is not None else []
        with Session(self.engine) as db:
            total = (
                db.scalar(select(func.count()).select_from(WaitReport).where(*scope))
                or 0
            )
            reports = db.scalars(
                select(WaitReport).where(
                    WaitReport.received_at > now - timedelta(minutes=60), *scope
                )
            ).all()
            by_queue: dict[tuple[str, str], list[WaitReport]] = defaultdict(list)
            for report in reports:
                by_queue[(report.venue_id, report.queue_kind)].append(report)
            fresh = sum(
                aggregate(values, now).count > 0 for values in by_queue.values()
            )
            # Count pseudonymous devices with reports on two distinct UTC days; never expose hashes.
            returning = (
                select(WaitReport.device_hash)
                .where(WaitReport.received_at > now - timedelta(days=7), *scope)
                .group_by(WaitReport.device_hash)
                .having(
                    func.count(func.distinct(func.date(WaitReport.received_at))) >= 2
                )
                .subquery()
            )
            repeat = db.scalar(select(func.count()).select_from(returning)) or 0
            return dict(
                reports_total=total,
                fresh_venue_queues=fresh,
                returning_devices_7d=repeat,
                checked_at=now,
            )
