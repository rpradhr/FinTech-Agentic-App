"""ID generation utilities."""
from __future__ import annotations

import uuid
from datetime import datetime


def new_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional prefix, e.g. 'FRAUD-' -> 'FRAUD-<uuid4>'."""
    uid = str(uuid.uuid4()).replace("-", "")[:16].upper()
    return f"{prefix}{uid}" if prefix else uid


def new_audit_id() -> str:
    return new_id("AUD-")


def new_fraud_id() -> str:
    return new_id("FRAUD-")


def new_loan_id() -> str:
    return new_id("LOAN-")


def new_review_id() -> str:
    return new_id("REV-")


def new_case_id() -> str:
    return new_id("CASE-")


def new_draft_id() -> str:
    return new_id("ADV-")


def new_trace_id() -> str:
    return new_id("TRC-")


def new_session_id() -> str:
    return new_id("SES-")


def new_interaction_id() -> str:
    return new_id("INT-")


def new_analysis_id() -> str:
    return new_id("ANA-")


def new_branch_insight_id() -> str:
    return new_id("BRN-")
