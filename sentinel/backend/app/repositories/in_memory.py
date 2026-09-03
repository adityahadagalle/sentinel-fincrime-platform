"""
In-Memory Case Repository Implementation for SENTINEL (Phase 7).

Satisfies AbstractCaseRepository contract for fast unit testing and dependency injection
without requiring a running PostgreSQL server.
"""

import copy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.repositories.base import AbstractCaseRepository


class InMemoryCaseRepository(AbstractCaseRepository):
    """
    In-Memory persistence implementation satisfying the AbstractCaseRepository contract.
    """

    def __init__(self, store: Optional[Dict[str, Any]] = None):
        self._cases: Dict[str, Dict[str, Any]] = {}
        self._dispositions: Dict[str, List[Dict[str, Any]]] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._idempotency_index: Dict[str, Dict[str, Any]] = {}
        self._locked_cases: set = set()
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._inv_runs: Dict[str, Dict[str, Any]] = {}

        if store is not None:
            self._cases = store.setdefault("cases", {})
            self._dispositions = store.setdefault("dispositions", {})
            self._audit_log = store.setdefault("audit_log", [])
            self._accounts = store.setdefault("accounts", {})
            self._transactions = store.setdefault("transactions", {})
            self._reports = store.setdefault("investigation_reports", {})
            self._inv_runs = store.setdefault("investigation_runs", {})



    async def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:

        case = self._cases.get(case_id)
        return copy.deepcopy(case) if case else None

    async def get_case_for_update(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Simulates pessimistic FOR UPDATE lock by checking case existence."""
        case = self._cases.get(case_id)
        if not case:
            return None
        self._locked_cases.add(case_id)
        return copy.deepcopy(case)

    async def get_disposition_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if not idempotency_key:
            return None
        disp = self._idempotency_index.get(idempotency_key)
        return copy.deepcopy(disp) if disp else None

    async def save_disposition_and_audit(
        self,
        case_id: str,
        new_status: str,
        disposition_record: Dict[str, Any],
        audit_event_record: Dict[str, Any]
    ) -> bool:
        case = self._cases.get(case_id)
        if not case:
            return False

        idempotency_key = disposition_record.get("idempotency_key")
        if idempotency_key and idempotency_key in self._idempotency_index:
            raise ValueError(f"Duplicate idempotency_key '{idempotency_key}'")

        # 1. Update Case
        case["status"] = new_status
        case["last_disposition_id"] = disposition_record.get("disposition_id")
        case["last_disposition_code"] = disposition_record.get("action_code")
        case["last_disposition_timestamp"] = disposition_record.get("disposition_timestamp")
        case["version"] = case.get("version", 1) + 1

        # 2. Add Disposition
        disp = copy.deepcopy(disposition_record)
        if case_id not in self._dispositions:
            self._dispositions[case_id] = []
        self._dispositions[case_id].append(disp)

        if idempotency_key:
            self._idempotency_index[idempotency_key] = disp

        # 3. Add Audit Event
        audit = copy.deepcopy(audit_event_record)
        self._audit_log.append(audit)

        if case_id in self._locked_cases:
            self._locked_cases.remove(case_id)

        return True

    async def get_case_history(self, case_id: str) -> Dict[str, Any]:
        case = self._cases.get(case_id)
        if not case:
            return {
                "found": False,
                "case_id": case_id,
                "current_case_status": None,
                "disposition_history": [],
                "audit_history": []
            }

        disps = copy.deepcopy(self._dispositions.get(case_id, []))
        audits = [copy.deepcopy(a) for a in self._audit_log if a.get("case_id") == case_id]

        # Chronological sorting
        disps.sort(key=lambda x: (x.get("disposition_timestamp", ""), x.get("disposition_id", "")))
        audits.sort(key=lambda x: (x.get("timestamp", ""), x.get("audit_id", "")))

        return {
            "found": True,
            "case_id": case_id,
            "current_case_status": case["status"],
            "disposition_history": disps,
            "audit_history": audits
        }

    async def save_case(self, case_record: Dict[str, Any]) -> bool:
        self._cases[case_record["case_id"]] = copy.deepcopy(case_record)
        return True

    async def save_investigation_report(self, report_record: Dict[str, Any]) -> bool:
        case_id = report_record["case_id"]
        if case_id not in self._cases:
            raise KeyError(f"Case '{case_id}' not found.")
        report_type = report_record["report_type"]
        key = f"{case_id}::{report_type}"
        self._reports[key] = copy.deepcopy(report_record)
        return True

    async def get_investigation_report(self, case_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        key = f"{case_id}::{report_type}"
        rpt = self._reports.get(key)
        return copy.deepcopy(rpt) if rpt else None

    async def get_investigation_reports_by_case_id(self, case_id: str) -> List[Dict[str, Any]]:

        rpts = [copy.deepcopy(r) for k, r in self._reports.items() if r.get("case_id") == case_id]
        rpts.sort(key=lambda x: (x.get("created_at", ""), x.get("report_id", "")))
        return rpts

    async def save_audit_event(self, audit_event_record: Dict[str, Any]) -> bool:
        if "audit_events" not in self._store:
            self._store["audit_events"] = []
        self._store["audit_events"].append(copy.deepcopy(audit_event_record))
        return True



    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        acc = self._accounts.get(account_id)
        return copy.deepcopy(acc) if acc else None

    async def save_account(self, account_record: Dict[str, Any]) -> bool:
        acc_id = account_record["account_id"]
        self._accounts[acc_id] = copy.deepcopy(account_record)
        return True

    async def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        tx = self._transactions.get(tx_id)
        return copy.deepcopy(tx) if tx else None

    async def save_transaction(self, tx_record: Dict[str, Any]) -> bool:
        tx_id = tx_record["tx_id"]
        self._transactions[tx_id] = copy.deepcopy(tx_record)
        return True

    async def save_transaction_and_case(
        self,
        accounts: List[Dict[str, Any]],
        tx_record: Dict[str, Any],
        case_record: Optional[Dict[str, Any]]
    ) -> bool:
        for acc in accounts:
            acc_id = acc["account_id"]
            if acc_id not in self._accounts:
                self._accounts[acc_id] = copy.deepcopy(acc)
        tx_id = tx_record["tx_id"]
        self._transactions[tx_id] = copy.deepcopy(tx_record)
        if case_record:
            case_id = case_record["case_id"]
            self._cases[case_id] = copy.deepcopy(case_record)
        return True

    async def get_cases(self) -> List[Dict[str, Any]]:
        cases = [copy.deepcopy(c) for c in self._cases.values()]
        cases.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return cases

    async def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        txs = [copy.deepcopy(t) for t in self._transactions.values()]
        txs.sort(key=lambda x: str(x.get("timestamp") or x.get("created_at", "")), reverse=True)
        return txs[:limit]

    async def get_all_transactions(self) -> List[Dict[str, Any]]:
        txs = [copy.deepcopy(t) for t in self._transactions.values()]
        txs.sort(key=lambda x: str(x.get("timestamp") or x.get("created_at", "")))
        return txs

    async def get_all_audit_events(self) -> List[Dict[str, Any]]:
        return [copy.deepcopy(a) for a in self._audit_log]

    async def save_investigation_run(self, run_record: Dict[str, Any]) -> bool:
        run_id = run_record["run_id"]
        self._inv_runs[run_id] = copy.deepcopy(run_record)
        return True

    async def get_investigation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        r = self._inv_runs.get(run_id)
        return copy.deepcopy(r) if r else None

    async def get_active_investigation_run(self, case_id: str) -> Optional[Dict[str, Any]]:
        for r in self._inv_runs.values():
            if r.get("case_id") == case_id and r.get("status") == "RUNNING":
                return copy.deepcopy(r)
        return None

    async def get_latest_investigation_run(self, case_id: str) -> Optional[Dict[str, Any]]:
        runs = [copy.deepcopy(r) for r in self._inv_runs.values() if r.get("case_id") == case_id]
        if not runs:
            return None
        runs.sort(key=lambda x: str(x.get("started_at", "")), reverse=True)
        return runs[0]

    async def get_investigation_runs_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        runs = [copy.deepcopy(r) for r in self._inv_runs.values() if r.get("case_id") == case_id]
        runs.sort(key=lambda x: str(x.get("started_at", "")), reverse=True)
        return runs


    async def recover_stale_investigation_runs(self, stale_threshold_seconds: int = 600) -> int:
        recovered = 0
        now = datetime.now(timezone.utc)
        for r in self._inv_runs.values():
            if r.get("status") == "RUNNING":
                r["status"] = "FAILED"
                r.setdefault("summary", {}).setdefault("degraded_reasons", []).append("STALE_RUN_PROCESS_RESTART_RECOVERY")
                r["completed_at"] = now.isoformat().replace("+00:00", "Z")
                recovered += 1
        return recovered

    async def get_case_for_update(self, case_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_case_by_id(case_id)

    async def commit_transaction(self) -> None:
        pass

    async def rollback_transaction(self) -> None:
        pass
