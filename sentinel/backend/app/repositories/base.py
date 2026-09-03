"""
Abstract Case Repository Interface for SENTINEL (Phase 7).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class AbstractCaseRepository(ABC):
    """
    Abstract contract for case lifecycle, disposition, and audit persistence operations.
    Exposes no update/delete methods for audit log entries (append-only audit boundary).
    """

    @abstractmethod
    async def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch case record by case_id without pessimistic locking."""
        pass

    @abstractmethod
    async def get_case_for_update(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch case record by case_id with a pessimistic row lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def get_disposition_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Lookup existing disposition record by idempotency key."""
        pass

    @abstractmethod
    async def save_disposition_and_audit(
        self,
        case_id: str,
        new_status: str,
        disposition_record: Dict[str, Any],
        audit_event_record: Dict[str, Any]
    ) -> bool:
        """
        Atomically executes:
        1. Insertion of disposition record.
        2. Case status update and timestamp modification.
        3. Insertion of immutable audit event record.
        """
        pass

    @abstractmethod
    async def save_audit_event(self, audit_event_record: Dict[str, Any]) -> bool:
        """
        Appends an immutable audit event record to the audit log repository.
        Exposes no mutation or deletion capabilities (append-only).
        """
        pass

    @abstractmethod
    async def get_case_history(self, case_id: str) -> Dict[str, Any]:

        """
        Retrieves complete chronological disposition and audit log history for a given case.
        Returns dict containing:
        - current_case_status
        - disposition_history
        - audit_history
        """
        pass

    @abstractmethod
    async def save_case(self, case_record: Dict[str, Any]) -> bool:
        """Saves or initializes a case entity."""
        pass

    @abstractmethod
    async def save_investigation_report(self, report_record: Dict[str, Any]) -> bool:
        """Saves or updates an investigation report artifact associated with a case."""
        pass

    @abstractmethod
    async def get_investigation_report(self, case_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        """Fetch investigation report by case_id and report_type."""
        pass

    @abstractmethod
    async def get_investigation_reports_by_case_id(self, case_id: str) -> List[Dict[str, Any]]:
        """Fetch all investigation reports for a given case_id."""
        pass


    @abstractmethod
    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Fetch account record by account_id."""
        pass

    @abstractmethod
    async def save_account(self, account_record: Dict[str, Any]) -> bool:
        """Saves or updates an account entity."""
        pass

    @abstractmethod
    async def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Fetch transaction record by tx_id."""
        pass

    @abstractmethod
    async def save_transaction(self, tx_record: Dict[str, Any]) -> bool:
        """Saves a transaction entity."""
        pass

    @abstractmethod
    async def save_transaction_and_case(
        self,
        accounts: List[Dict[str, Any]],
        tx_record: Dict[str, Any],
        case_record: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Atomically executes in one database transaction:
        1. Account creation/update for all provided accounts.
        2. Transaction creation.
        3. Case creation/update (if case_record is present).
        """
        pass

    @abstractmethod
    async def get_cases(self) -> List[Dict[str, Any]]:
        """Fetch all cases ordered by created_at descending."""
        pass

    @abstractmethod
    async def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent transactions for WebSocket hydration."""
        pass

    @abstractmethod
    async def get_all_transactions(self) -> List[Dict[str, Any]]:
        """Fetch all transactions for CSV export."""
        pass

    @abstractmethod
    async def get_all_audit_events(self) -> List[Dict[str, Any]]:
        """Fetch all audit events/actions for CSV export."""
        pass

    @abstractmethod
    async def save_investigation_run(self, run_record: Dict[str, Any]) -> bool:
        """Saves or updates a durable InvestigationRun record."""
        pass

    @abstractmethod
    async def get_investigation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Fetch investigation run by run_id."""
        pass

    @abstractmethod
    async def get_active_investigation_run(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch active (RUNNING) investigation run for case_id."""
        pass

    @abstractmethod
    async def get_latest_investigation_run(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch most recent investigation run for case_id."""
        pass

    @abstractmethod
    async def get_investigation_runs_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        """Fetch all historical investigation runs for case_id ordered by started_at DESC."""
        pass


    @abstractmethod
    async def recover_stale_investigation_runs(self, stale_threshold_seconds: int = 600) -> int:
        """Finds active RUNNING investigations older than threshold and marks them FAILED/DEGRADED due to restart."""
        pass

    @abstractmethod
    async def get_case_for_update(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch case with SELECT FOR UPDATE row lock to serialize concurrent operations across processes."""
        pass

    @abstractmethod
    async def commit_transaction(self) -> None:
        """Commits current database transaction boundary."""
        pass

    @abstractmethod
    async def rollback_transaction(self) -> None:
        """Rolls back current database transaction boundary."""
        pass
