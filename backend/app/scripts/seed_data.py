"""
Seed script — populates the datastore with sample banking data for local dev.

Usage:
    python -m app.scripts.seed_data           # uses configured backend
    python -m app.scripts.seed_data --dry-run # prints what would be seeded
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta

from app.core.config import get_settings
from app.core.container import Container
from app.domain.models import (
    BranchKPI,
    CustomerProfile,
    Household,
    Interaction,
    LoanApplication,
    Transaction,
)
from app.domain.models.customer import KYCStatus, RiskTolerance, SentimentStatus
from app.domain.models.interaction import InteractionSource
from app.domain.models.transaction import TransactionChannel, TransactionStatus

SAMPLE_CUSTOMERS = [
    CustomerProfile(
        customer_id="C-ASHA001",
        household_id="H-001",
        name="Asha Mehta",
        email="asha@example.com",
        risk_tolerance=RiskTolerance.MODERATE,
        products=["checking", "credit_card", "auto_loan"],
        goals=["emergency_fund", "college_savings"],
        kyc_status=KYCStatus.VERIFIED,
        last_sentiment_status=SentimentStatus.NEGATIVE,
    ),
    CustomerProfile(
        customer_id="C-JAMES002",
        household_id="H-002",
        name="James Okafor",
        email="james@example.com",
        risk_tolerance=RiskTolerance.AGGRESSIVE,
        products=["checking", "investment_account"],
        goals=["retirement", "emergency_fund"],
        kyc_status=KYCStatus.VERIFIED,
    ),
    CustomerProfile(
        customer_id="C-SARA003",
        household_id="H-001",
        name="Sara Mehta",
        email="sara@example.com",
        risk_tolerance=RiskTolerance.CONSERVATIVE,
        products=["savings", "cd"],
        goals=["home_purchase"],
        kyc_status=KYCStatus.VERIFIED,
    ),
]

SAMPLE_TRANSACTIONS = [
    Transaction(
        txn_id="T-001",
        customer_id="C-ASHA001",
        account_id="A-1001",
        amount=4200.55,
        merchant="MERCHANT_7781",
        channel=TransactionChannel.CARD_PRESENT,
        device_id="D-991",
        status=TransactionStatus.FLAGGED,
        event_ts=datetime.utcnow() - timedelta(hours=2),
    ),
    Transaction(
        txn_id="T-002",
        customer_id="C-ASHA001",
        account_id="A-1001",
        amount=125.00,
        merchant="GROCERY_MART",
        channel=TransactionChannel.CARD_PRESENT,
        event_ts=datetime.utcnow() - timedelta(days=1),
    ),
    Transaction(
        txn_id="T-003",
        customer_id="C-JAMES002",
        account_id="A-2001",
        amount=15000.00,
        channel=TransactionChannel.WIRE,
        event_ts=datetime.utcnow() - timedelta(hours=5),
    ),
]

SAMPLE_INTERACTIONS = [
    Interaction(
        interaction_id="INT-001",
        customer_id="C-ASHA001",
        source=InteractionSource.CALL_TRANSCRIPT,
        content=(
            "Customer called to dispute a fee reversal that has been pending for 3 weeks. "
            "She expressed frustration repeatedly and mentioned she's considering moving "
            "her accounts to a competitor bank. The agent tried to explain the delay but "
            "the customer was not satisfied with the response. Tone was escalating."
        ),
        branch_id="BR-WEST01",
    ),
    Interaction(
        interaction_id="INT-002",
        customer_id="C-JAMES002",
        source=InteractionSource.EMAIL,
        content=(
            "Hi, I wanted to reach out to say how much I appreciate the service I received "
            "from my advisor last week. The investment recommendations were spot on and I feel "
            "very confident in my portfolio. Thank you!"
        ),
    ),
]

SAMPLE_LOAN_APPLICATIONS = [
    LoanApplication(
        application_id="L-001",
        customer_id="C-ASHA001",
        loan_type="personal",
        requested_amount=25000.0,
        term_months=60,
        stated_income=120000.0,
        stated_employment="Software Engineer",
        credit_score=720,
        submitted_docs=["paystub", "id_doc"],  # Missing bank_statement
    ),
]

SAMPLE_BRANCH_KPIS = [
    BranchKPI(
        kpi_id=f"KPI-BR-WEST01-{i}",
        branch_id="BR-WEST01",
        branch_name="West Side Branch",
        region="West",
        report_date=date.today() - timedelta(days=i),
        avg_wait_time_minutes=12.0 + i * 1.5,  # Increasing wait times
        complaint_count=3 + i,
        new_accounts_opened=max(0, 8 - i),  # Declining accounts
        scheduled_staff=10,
        actual_staff=10 - (i // 3),  # Staffing gap emerging
        teller_transactions=200 - i * 5,
        atm_transactions=150,
    )
    for i in range(7)
]


async def seed(dry_run: bool = False) -> None:
    settings = get_settings()
    container = Container(settings)
    await container.connect()

    print(f"Seeding to backend: {settings.database_backend}")

    for customer in SAMPLE_CUSTOMERS:
        if not dry_run:
            await container.customers.save(customer)
        print(f"  Customer: {customer.customer_id} — {customer.name}")

    household = Household(
        household_id="H-001",
        member_customer_ids=["C-ASHA001", "C-SARA003"],
        primary_customer_id="C-ASHA001",
    )
    if not dry_run:
        await container.customers.save_household(household)
    print(f"  Household: {household.household_id}")

    for txn in SAMPLE_TRANSACTIONS:
        if not dry_run:
            await container.transactions.save(txn)
        print(f"  Transaction: {txn.txn_id} — {txn.amount}")

    for interaction in SAMPLE_INTERACTIONS:
        if not dry_run:
            await container.interactions.save_interaction(interaction)
        print(f"  Interaction: {interaction.interaction_id}")

    for loan in SAMPLE_LOAN_APPLICATIONS:
        if not dry_run:
            await container.loans.save_application(loan)
        print(f"  Loan application: {loan.application_id}")

    for kpi in SAMPLE_BRANCH_KPIS:
        if not dry_run:
            await container.branches.save_kpi(kpi)
    print(f"  Branch KPIs: {len(SAMPLE_BRANCH_KPIS)} records for BR-WEST01")

    await container.close()
    print("\nSeed complete." if not dry_run else "\nDry run complete — no data written.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(seed(dry_run=dry_run))
