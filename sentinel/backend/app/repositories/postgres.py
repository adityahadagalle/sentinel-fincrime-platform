"""
PostgreSQL Case Repository Implementation for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.account import Account
from app.models.transaction import Transaction
from app.models.case import Case
from app.models.disposition import Disposition
from app.models.audit_event import AuditEvent
from app.models.investigation_report import InvestigationReport
from app.models.investigation_run import InvestigationRun
from app.repositories.base import AbstractCaseRepository


def _inv_run_to_dict(r: InvestigationRun) -> Dict[str, Any]:
    return {
        "run_id": r.run_id,
        "investigation_id": r.run_id,
        "case_id": r.case_id,
        "status": r.status,
        "current_stage": r.current_stage,
        "stages": r.stage_states or {},
        "stage_states": r.stage_states or {},
        "summary": r.summary or {},
        "retry_count": r.retry_count,
        "force_rerun": r.force_rerun,
        "started_at": r.started_at.isoformat().replace("+00:00", "Z") if r.started_at else None,
        "completed_at": r.completed_at.isoformat().replace("+00:00", "Z") if r.completed_at else None,
        "created_at": r.created_at.isoformat().replace("+00:00", "Z") if r.created_at else None,
        "updated_at": r.updated_at.isoformat().replace("+00:00", "Z") if r.updated_at else None,
    }



def _account_to_dict(a: Account) -> Dict[str, Any]:
    return {
        "account_id": a.account_id,
        "kyc_status": a.kyc_status,
        "risk_score": float(a.risk_score or 0.0),
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None
    }


def _transaction_to_dict(t: Transaction) -> Dict[str, Any]:
    return {
        "tx_id": t.tx_id,
        "sender_account": t.sender_account_id,
        "receiver_account": t.receiver_account_id,
        "amount": float(t.amount or 0.0),
        "currency": t.currency,
        "channel": t.channel,
        "timestamp": t.timestamp.isoformat() if t.timestamp else None,
        "raw_payload": t.raw_payload or {},
        "created_at": t.created_at.isoformat() if t.created_at else None
    }



def _parse_iso(val: Any) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    return None


def _case_to_dict(c: Case) -> Dict[str, Any]:
    return {
        "case_id": c.case_id,
        "primary_tx_id": c.primary_tx_id,
        "status": c.status,
        "risk_level": c.risk_level,
        "golden_window_minutes": c.golden_window_minutes,
        "total_fraud_amount": float(c.total_fraud_amount or 0.0),
        "recoverable_amount": float(c.recoverable_amount or 0.0),
        "last_disposition_id": c.last_disposition_id,
        "last_disposition_code": c.last_disposition_code,
        "last_disposition_timestamp": c.last_disposition_timestamp.isoformat() if c.last_disposition_timestamp else None,
        "version": c.version,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None
    }


def _disposition_to_dict(d: Disposition) -> Dict[str, Any]:
    return {
        "disposition_id": d.disposition_id,
        "case_id": d.case_id,
        "primary_tx_id": d.primary_tx_id,
        "action_code": d.action_code,
        "label": d.label,
        "analyst_notes": d.analyst_notes,
        "analyst_id": d.analyst_id,
        "analyst_role": d.analyst_role,
        "risk_acknowledged": d.risk_acknowledged,
        "previous_case_status": d.previous_case_status,
        "new_case_status": d.new_case_status,
        "idempotency_key": d.idempotency_key,
        "disposition_timestamp": d.timestamp.isoformat() if d.timestamp else None
    }


def _audit_to_dict(a: AuditEvent) -> Dict[str, Any]:
    return {
        "audit_id": a.audit_id,
        "event_type": a.event_type,
        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        "case_id": a.case_id,
        "primary_tx_id": a.primary_tx_id,
        "analyst_id": a.analyst_id,
        "analyst_role": a.analyst_role,
        "action_code": a.action_code,
        "previous_case_status": a.previous_case_status,
        "new_case_status": a.new_case_status,
        "analyst_notes": a.analyst_notes,
        "risk_acknowledged": a.risk_acknowledged,
        "decision_support_summary": a.decision_support_summary or {},
        "traceability_chain": a.traceability_chain or {}
    }


def _report_to_dict(r: InvestigationReport) -> Dict[str, Any]:
    return {
        "report_id": r.report_id,
        "case_id": r.case_id,
        "report_type": r.report_type,
        "report_data": r.report_data or {},
        "created_at": r.created_at.isoformat() if r.created_at else None
    }


class PostgreSQLCaseRepository(AbstractCaseRepository):

    """
    PostgreSQL persistence repository implementing pessimistic FOR UPDATE row locking,
    atomic multi-statement transactions, idempotency handling, and append-only audit tracking.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(Case).filter(Case.case_id == case_id)
        res = await self.session.execute(stmt)
        case_obj = res.scalar_one_or_none()
        return _case_to_dict(case_obj) if case_obj else None

    async def get_case_for_update(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Executes SELECT * FROM cases WHERE case_id = :case_id FOR UPDATE.
        Pessimistic row lock remains held on the session until commit/rollback.
        """
        stmt = select(Case).filter(Case.case_id == case_id).with_for_update()
        res = await self.session.execute(stmt)
        case_obj = res.scalar_one_or_none()
        return _case_to_dict(case_obj) if case_obj else None

    async def get_disposition_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if not idempotency_key:
            return None
        stmt = select(Disposition).filter(Disposition.idempotency_key == idempotency_key)
        res = await self.session.execute(stmt)
        disp_obj = res.scalar_one_or_none()
        return _disposition_to_dict(disp_obj) if disp_obj else None

    async def save_disposition_and_audit(
        self,
        case_id: str,
        new_status: str,
        disposition_record: Dict[str, Any],
        audit_event_record: Dict[str, Any]
    ) -> bool:
        """
        Atomically executes disposition INSERT, case status UPDATE, and audit_event INSERT.
        If any statement fails, exception propagates to cause transaction rollback.
        """
        try:
            # 1. Fetch case for update
            stmt = select(Case).filter(Case.case_id == case_id).with_for_update()
            res = await self.session.execute(stmt)
            case_obj = res.scalar_one_or_none()
            if not case_obj:
                return False

            ts_dt = _parse_iso(disposition_record.get("disposition_timestamp")) or datetime.now(timezone.utc)
            audit_ts_dt = _parse_iso(audit_event_record.get("timestamp")) or datetime.now(timezone.utc)

            # 2. Update case entity
            case_obj.status = new_status
            case_obj.last_disposition_id = disposition_record.get("disposition_id")
            case_obj.last_disposition_code = disposition_record.get("action_code")
            case_obj.last_disposition_timestamp = ts_dt
            case_obj.updated_at = datetime.now(timezone.utc)
            case_obj.version += 1

            # 3. Create Disposition entity
            disp_obj = Disposition(
                disposition_id=disposition_record.get("disposition_id"),
                case_id=case_id,
                primary_tx_id=disposition_record.get("primary_tx_id"),
                action_code=disposition_record.get("action_code"),
                label=disposition_record.get("label", disposition_record.get("action_code")),
                analyst_notes=disposition_record.get("analyst_notes", ""),
                analyst_id=disposition_record.get("analyst_id"),
                analyst_role=disposition_record.get("analyst_role"),
                risk_acknowledged=bool(disposition_record.get("risk_acknowledged", False)),
                previous_case_status=disposition_record.get("previous_case_status"),
                new_case_status=new_status,
                idempotency_key=disposition_record.get("idempotency_key"),
                timestamp=ts_dt
            )
            self.session.add(disp_obj)

            # 4. Create AuditEvent entity
            audit_obj = AuditEvent(
                audit_id=audit_event_record.get("audit_id"),
                event_type=audit_event_record.get("event_type", "CASE_DISPOSITION_MUTATION"),
                case_id=case_id,
                primary_tx_id=audit_event_record.get("primary_tx_id"),
                analyst_id=audit_event_record.get("analyst_id"),
                analyst_role=audit_event_record.get("analyst_role"),
                action_code=audit_event_record.get("action_code"),
                previous_case_status=audit_event_record.get("previous_case_status"),
                new_case_status=new_status,
                analyst_notes=audit_event_record.get("analyst_notes", ""),
                risk_acknowledged=bool(audit_event_record.get("risk_acknowledged", False)),
                decision_support_summary=audit_event_record.get("decision_support_summary", {}),
                traceability_chain=audit_event_record.get("traceability_chain", {}),
                timestamp=audit_ts_dt
            )
            self.session.add(audit_obj)

            await self.session.flush()
            return True
        except IntegrityError:
            await self.session.rollback()
            raise

    async def save_audit_event(self, audit_event_record: Dict[str, Any]) -> bool:
        case_id = audit_event_record.get("case_id")
        if not case_id:
            return False

        # Verify case_id exists in cases table before inserting audit_event
        case_obj = await self.session.get(Case, case_id)
        if not case_obj:
            return False

        ts_val = audit_event_record.get("timestamp")
        if isinstance(ts_val, datetime):
            audit_ts_dt = ts_val
        elif isinstance(ts_val, str) and ts_val:
            audit_ts_dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
        else:
            audit_ts_dt = datetime.now(timezone.utc)

        audit_obj = AuditEvent(
            audit_id=audit_event_record.get("audit_id"),
            event_type=audit_event_record.get("event_type", "AUTOMATED_ACTION_EXECUTED"),
            case_id=case_id,
            primary_tx_id=audit_event_record.get("primary_tx_id"),
            analyst_id=audit_event_record.get("analyst_id", "SYSTEM_AUTOMATION"),
            analyst_role=audit_event_record.get("analyst_role", "AUTOMATION_ENGINE"),
            action_code=audit_event_record.get("action_code", "UNKNOWN_ACTION"),
            previous_case_status=audit_event_record.get("previous_case_status", "NEW"),
            new_case_status=audit_event_record.get("new_case_status", "IN_PROGRESS"),
            analyst_notes=audit_event_record.get("analyst_notes", ""),
            risk_acknowledged=bool(audit_event_record.get("risk_acknowledged", False)),
            decision_support_summary=audit_event_record.get("decision_support_summary", {}),
            traceability_chain=audit_event_record.get("traceability_chain", {}),
            timestamp=audit_ts_dt
        )
        self.session.add(audit_obj)
        try:
            await self.session.flush()
            return True
        except IntegrityError:
            return False


    async def get_case_history(self, case_id: str) -> Dict[str, Any]:

        case_dict = await self.get_case_by_id(case_id)
        if not case_dict:
            return {
                "found": False,
                "case_id": case_id,
                "current_case_status": None,
                "disposition_history": [],
                "audit_history": []
            }

        # Chronological dispositions query
        disp_stmt = select(Disposition).filter(Disposition.case_id == case_id).order_by(
            Disposition.timestamp.asc(),
            Disposition.created_at.asc(),
            Disposition.disposition_id.asc()
        )
        disp_res = await self.session.execute(disp_stmt)
        dispositions = [_disposition_to_dict(d) for d in disp_res.scalars().all()]

        # Chronological audit events query
        audit_stmt = select(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(
            AuditEvent.timestamp.asc(),
            AuditEvent.created_at.asc(),
            AuditEvent.audit_id.asc()
        )
        audit_res = await self.session.execute(audit_stmt)
        audit_log = [_audit_to_dict(a) for a in audit_res.scalars().all()]

        return {
            "found": True,
            "case_id": case_id,
            "current_case_status": case_dict["status"],
            "disposition_history": dispositions,
            "audit_history": audit_log
        }

    async def save_case(self, case_record: Dict[str, Any]) -> bool:
        created_dt = _parse_iso(case_record.get("created_at")) or datetime.now(timezone.utc)
        case_obj = Case(
            case_id=case_record["case_id"],
            primary_tx_id=case_record["primary_tx_id"],
            status=case_record.get("status", "NEW"),
            risk_level=case_record.get("risk_level", "LOW"),
            golden_window_minutes=int(case_record.get("golden_window_minutes", 30)),
            total_fraud_amount=float(case_record.get("total_fraud_amount", 0.0)),
            recoverable_amount=float(case_record.get("recoverable_amount", 0.0)),
            created_at=created_dt,
            updated_at=created_dt
        )
        self.session.add(case_obj)
        await self.session.flush()
        return True

    async def save_investigation_report(self, report_record: Dict[str, Any]) -> bool:
        """
        Upserts an InvestigationReport for (case_id, report_type).
        If case_id does not exist, foreign key constraint raises IntegrityError.
        """
        try:
            case_id = report_record["case_id"]
            report_type = report_record["report_type"]
            created_dt = _parse_iso(report_record.get("created_at")) or datetime.now(timezone.utc)
            rpt_data = report_record.get("report_data", report_record)

            stmt = select(InvestigationReport).filter(
                InvestigationReport.case_id == case_id,
                InvestigationReport.report_type == report_type
            )
            res = await self.session.execute(stmt)
            rpt_obj = res.scalar_one_or_none()

            if rpt_obj:
                rpt_obj.report_data = rpt_data
                rpt_obj.created_at = created_dt
            else:
                report_id = report_record.get("report_id") or f"RPT-{case_id}-{report_type}"
                rpt_obj = InvestigationReport(
                    report_id=report_id,
                    case_id=case_id,
                    report_type=report_type,
                    report_data=rpt_data,
                    created_at=created_dt
                )
                self.session.add(rpt_obj)

            await self.session.flush()
            return True
        except IntegrityError:
            await self.session.rollback()
            raise

    async def get_investigation_report(self, case_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        stmt = select(InvestigationReport).filter(
            InvestigationReport.case_id == case_id,
            InvestigationReport.report_type == report_type
        )
        res = await self.session.execute(stmt)
        rpt_obj = res.scalar_one_or_none()
        return _report_to_dict(rpt_obj) if rpt_obj else None

    async def get_investigation_reports_by_case_id(self, case_id: str) -> List[Dict[str, Any]]:
        stmt = select(InvestigationReport).filter(
            InvestigationReport.case_id == case_id
        ).order_by(InvestigationReport.created_at.asc(), InvestigationReport.report_id.asc())
        res = await self.session.execute(stmt)
        reports = res.scalars().all()
        return [_report_to_dict(r) for r in reports]


    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(Account).filter(Account.account_id == account_id)
        res = await self.session.execute(stmt)
        acc_obj = res.scalar_one_or_none()
        return _account_to_dict(acc_obj) if acc_obj else None

    async def save_account(self, account_record: Dict[str, Any]) -> bool:
        acc_id = account_record["account_id"]
        stmt = select(Account).filter(Account.account_id == acc_id)
        res = await self.session.execute(stmt)
        acc_obj = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not acc_obj:
            acc_obj = Account(
                account_id=acc_id,
                kyc_status=account_record.get("kyc_status", "PENDING"),
                risk_score=float(account_record.get("risk_score", 0.0)),
                created_at=_parse_iso(account_record.get("created_at")) or now,
                updated_at=now
            )
            self.session.add(acc_obj)
        else:
            if "kyc_status" in account_record:
                acc_obj.kyc_status = account_record["kyc_status"]
            if "risk_score" in account_record:
                acc_obj.risk_score = float(account_record["risk_score"])
            acc_obj.updated_at = now
        await self.session.flush()
        return True

    async def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(Transaction).filter(Transaction.tx_id == tx_id)
        res = await self.session.execute(stmt)
        tx_obj = res.scalar_one_or_none()
        return _transaction_to_dict(tx_obj) if tx_obj else None

    async def save_transaction(self, tx_record: Dict[str, Any]) -> bool:
        tx_id = tx_record["tx_id"]
        stmt = select(Transaction).filter(Transaction.tx_id == tx_id)
        res = await self.session.execute(stmt)
        tx_obj = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        ts_dt = _parse_iso(tx_record.get("timestamp")) or now
        if not tx_obj:
            tx_obj = Transaction(
                tx_id=tx_id,
                sender_account_id=tx_record["sender_account"],
                receiver_account_id=tx_record["receiver_account"],
                amount=float(tx_record.get("amount", 0.0)),
                currency=tx_record.get("currency", "INR"),
                channel=tx_record.get("channel", "UPI"),
                timestamp=ts_dt,
                raw_payload=tx_record.get("raw_payload", tx_record),
                created_at=now
            )
            self.session.add(tx_obj)
            await self.session.flush()
        return True

    async def save_transaction_and_case(
        self,
        accounts: List[Dict[str, Any]],
        tx_record: Dict[str, Any],
        case_record: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Atomically persists accounts, transaction, and case entities in one DB transaction session.
        Flushes all SQL statements so FK constraints are verified before commit.
        """
        try:
            now = datetime.now(timezone.utc)

            # 1. Accounts
            for acc in accounts:
                acc_id = acc.get("account_id")
                if not acc_id:
                    continue
                acc_res = await self.session.execute(select(Account).filter(Account.account_id == acc_id))
                acc_obj = acc_res.scalar_one_or_none()
                if not acc_obj:
                    acc_obj = Account(
                        account_id=acc_id,
                        kyc_status=acc.get("kyc_status", "PENDING"),
                        risk_score=float(acc.get("risk_score", 0.0)),
                        created_at=_parse_iso(acc.get("created_at")) or now,
                        updated_at=now
                    )
                    self.session.add(acc_obj)

            await self.session.flush()

            # 2. Transaction
            tx_id = tx_record["tx_id"]
            tx_res = await self.session.execute(select(Transaction).filter(Transaction.tx_id == tx_id))
            tx_obj = tx_res.scalar_one_or_none()
            ts_dt = _parse_iso(tx_record.get("timestamp")) or now
            if not tx_obj:
                tx_obj = Transaction(
                    tx_id=tx_id,
                    sender_account_id=tx_record["sender_account"],
                    receiver_account_id=tx_record["receiver_account"],
                    amount=float(tx_record.get("amount", 0.0)),
                    currency=tx_record.get("currency", "INR"),
                    channel=tx_record.get("channel", "UPI"),
                    timestamp=ts_dt,
                    raw_payload=tx_record.get("raw_payload", tx_record),
                    created_at=now
                )
                self.session.add(tx_obj)

            await self.session.flush()

            # 3. Case (if present)
            if case_record and "case_id" in case_record:
                case_id = case_record["case_id"]
                case_res = await self.session.execute(select(Case).filter(Case.case_id == case_id))
                case_obj = case_res.scalar_one_or_none()

                raw_status = case_record.get("status", "NEW")
                valid_states = ("NEW", "UNDER_REVIEW", "CDD_PENDING", "ESCALATED", "RESOLVED_DISMISSED", "RESOLVED_APPROVED")
                c_status = raw_status if raw_status in valid_states else ("ESCALATED" if raw_status == "HIGH_RISK" else "NEW")

                if not case_obj:
                    case_created_dt = _parse_iso(case_record.get("created_at")) or now
                    case_obj = Case(
                        case_id=case_id,
                        primary_tx_id=tx_id,
                        status=c_status,
                        risk_level=str(case_record.get("risk_level", "LOW")),
                        golden_window_minutes=int(case_record.get("golden_window_minutes", 30)),
                        total_fraud_amount=float(case_record.get("total_fraud_amount", 0.0)),
                        recoverable_amount=float(case_record.get("recoverable_amount", 0.0)),
                        created_at=case_created_dt,
                        updated_at=case_created_dt
                    )
                    self.session.add(case_obj)
                else:
                    if raw_status in valid_states:
                        case_obj.status = raw_status
                    elif raw_status == "HIGH_RISK":
                        case_obj.status = "ESCALATED"
                    case_obj.risk_level = str(case_record.get("risk_level", case_obj.risk_level))
                    case_obj.total_fraud_amount = float(case_record.get("total_fraud_amount", case_obj.total_fraud_amount))
                    case_obj.updated_at = now

            await self.session.flush()
            return True

        except IntegrityError:
            await self.session.rollback()
            raise

    async def get_cases(self) -> List[Dict[str, Any]]:
        stmt = select(Case).order_by(Case.created_at.desc(), Case.case_id.desc())
        res = await self.session.execute(stmt)
        cases = res.scalars().all()
        return [_case_to_dict(c) for c in cases]

    async def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        stmt = select(Transaction).order_by(Transaction.timestamp.desc(), Transaction.created_at.desc()).limit(limit)
        res = await self.session.execute(stmt)
        txs = res.scalars().all()
        return [_transaction_to_dict(t) for t in txs]

    async def get_all_transactions(self) -> List[Dict[str, Any]]:
        stmt = select(Transaction).order_by(Transaction.timestamp.asc(), Transaction.created_at.asc())
        res = await self.session.execute(stmt)
        txs = res.scalars().all()
        return [_transaction_to_dict(t) for t in txs]

    async def get_all_audit_events(self) -> List[Dict[str, Any]]:
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.asc())
        res = await self.session.execute(stmt)
        events = res.scalars().all()
        return [_audit_to_dict(e) for e in events]

    async def save_investigation_run(self, run_record: Dict[str, Any]) -> bool:
        run_id = run_record["run_id"]
        case_id = run_record["case_id"]
        status = run_record.get("status", "RUNNING")
        current_stage = run_record.get("current_stage", "NONE")
        stage_states = run_record.get("stages") or run_record.get("stage_states") or {}
        summary = run_record.get("summary") or {}
        retry_count = int(run_record.get("retry_count", 0))
        force_rerun = bool(run_record.get("force_rerun", False))
        started_dt = _parse_iso(run_record.get("started_at")) or datetime.now(timezone.utc)
        completed_dt = _parse_iso(run_record.get("completed_at"))
        created_dt = _parse_iso(run_record.get("created_at")) or started_dt
        updated_dt = datetime.now(timezone.utc)

        stmt = select(InvestigationRun).filter(InvestigationRun.run_id == run_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()

        if obj:
            obj.status = status
            obj.current_stage = current_stage
            obj.stage_states = stage_states
            obj.summary = summary
            obj.retry_count = retry_count
            obj.force_rerun = force_rerun
            obj.completed_at = completed_dt
            obj.updated_at = updated_dt
        else:
            obj = InvestigationRun(
                run_id=run_id,
                case_id=case_id,
                status=status,
                current_stage=current_stage,
                stage_states=stage_states,
                summary=summary,
                retry_count=retry_count,
                force_rerun=force_rerun,
                started_at=started_dt,
                completed_at=completed_dt,
                created_at=created_dt,
                updated_at=updated_dt
            )
            self.session.add(obj)

        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return False
        return True


    async def get_investigation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(InvestigationRun).filter(InvestigationRun.run_id == run_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _inv_run_to_dict(obj) if obj else None

    async def get_active_investigation_run(self, case_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(InvestigationRun).filter(
            InvestigationRun.case_id == case_id,
            InvestigationRun.status == "RUNNING"
        ).order_by(InvestigationRun.started_at.desc()).with_for_update(of=InvestigationRun)
        res = await self.session.execute(stmt)
        obj = res.scalars().first()
        return _inv_run_to_dict(obj) if obj else None

    async def get_latest_investigation_run(self, case_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(InvestigationRun).filter(
            InvestigationRun.case_id == case_id
        ).order_by(InvestigationRun.started_at.desc())
        res = await self.session.execute(stmt)
        obj = res.scalars().first()
        return _inv_run_to_dict(obj) if obj else None

    async def get_investigation_runs_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        stmt = select(InvestigationRun).filter(
            InvestigationRun.case_id == case_id
        ).order_by(InvestigationRun.started_at.desc())
        res = await self.session.execute(stmt)
        objs = res.scalars().all()
        return [_inv_run_to_dict(o) for o in objs]


    async def recover_stale_investigation_runs(self, stale_threshold_seconds: int = 600) -> int:
        now = datetime.now(timezone.utc)
        threshold_dt = datetime.fromtimestamp(now.timestamp() - stale_threshold_seconds, timezone.utc)

        stmt = select(InvestigationRun).filter(
            InvestigationRun.status == "RUNNING",
            InvestigationRun.updated_at < threshold_dt
        ).with_for_update()
        res = await self.session.execute(stmt)
        stale_runs = res.scalars().all()

        recovered_count = 0
        for r in stale_runs:
            r.status = "FAILED"
            r.completed_at = now
            sum_dict = dict(r.summary or {})
            reasons = list(sum_dict.get("degraded_reasons", []))
            reasons.append("STALE_RUN_PROCESS_RESTART_RECOVERY")
            sum_dict["degraded_reasons"] = reasons
            r.summary = sum_dict
            r.updated_at = now
            recovered_count += 1

        if recovered_count > 0:
            await self.session.flush()

        return recovered_count

    async def get_case_for_update(self, case_id: str) -> Optional[Dict[str, Any]]:
        stmt = select(Case).filter(Case.case_id == case_id).with_for_update(of=Case)
        res = await self.session.execute(stmt)
        c = res.scalar_one_or_none()
        return _case_to_dict(c) if c else None

    async def commit_transaction(self) -> None:
        await self.session.commit()

    async def rollback_transaction(self) -> None:
        await self.session.rollback()
