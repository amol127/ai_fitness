# test_engine.py

import pandas as pd

from src.engine import detect_discrepancies

# =========================================================
# TEST: LATE_SETTLEMENT
# =========================================================

def test_late_settlement_gap():

    transactions = pd.DataFrame([
        {
            "transaction_id": "TXN001",
            "customer_id": "CUST001",
            "amount": 1000.00,
            "currency": "INR",
            "transaction_date": "2026-03-31",
            "status": "SUCCESS",
        }
    ])

    settlements = pd.DataFrame([
        {
            "settlement_id": "SET001",
            "transaction_id": "TXN001",
            "settled_amount": 1000.00,
            "settlement_date": "2026-04-01",
            "bank_reference": "BNK001",
        }
    ])

    gaps = detect_discrepancies(
        transactions,
        settlements,
    )

    gap_types = {
        gap["gap_type"]
        for gap in gaps
    }

    assert "LATE_SETTLEMENT" in gap_types


# =========================================================
# TEST: ROUNDING_DIFFERENCE
# =========================================================

def test_rounding_difference_gap():

    transactions = pd.DataFrame([
        {
            "transaction_id": "TXN002",
            "customer_id": "CUST002",
            "amount": 500.005,
            "currency": "INR",
            "transaction_date": "2026-03-15",
            "status": "SUCCESS",
        }
    ])

    settlements = pd.DataFrame([
        {
            "settlement_id": "SET002",
            "transaction_id": "TXN002",
            "settled_amount": 500.000,
            "settlement_date": "2026-03-16",
            "bank_reference": "BNK002",
        }
    ])

    gaps = detect_discrepancies(
        transactions,
        settlements,
    )

    gap_types = {
        gap["gap_type"]
        for gap in gaps
    }

    assert "ROUNDING_DIFFERENCE" in gap_types


# =========================================================
# TEST: DUPLICATE_SETTLEMENT
# =========================================================

def test_duplicate_settlement_gap():

    transactions = pd.DataFrame([
        {
            "transaction_id": "TXN003",
            "customer_id": "CUST003",
            "amount": 750.00,
            "currency": "INR",
            "transaction_date": "2026-03-10",
            "status": "SUCCESS",
        }
    ])

    settlements = pd.DataFrame([
        {
            "settlement_id": "SET003A",
            "transaction_id": "TXN003",
            "settled_amount": 750.00,
            "settlement_date": "2026-03-11",
            "bank_reference": "BNK003A",
        },
        {
            "settlement_id": "SET003B",
            "transaction_id": "TXN003",
            "settled_amount": 750.00,
            "settlement_date": "2026-03-11",
            "bank_reference": "BNK003B",
        }
    ])

    gaps = detect_discrepancies(
        transactions,
        settlements,
    )

    gap_types = {
        gap["gap_type"]
        for gap in gaps
    }

    assert "DUPLICATE_SETTLEMENT" in gap_types


# =========================================================
# TEST: ORPHAN_REFUND
# =========================================================

def test_orphan_refund_gap():

    transactions = pd.DataFrame(columns=[
        "transaction_id",
        "customer_id",
        "amount",
        "currency",
        "transaction_date",
        "status",
    ])

    settlements = pd.DataFrame([
        {
            "settlement_id": "SET004",
            "transaction_id": "TXN999",
            "settled_amount": -250.00,
            "settlement_date": "2026-03-20",
            "bank_reference": "BNK004",
        }
    ])

    gaps = detect_discrepancies(
        transactions,
        settlements,
    )

    gap_types = {
        gap["gap_type"]
        for gap in gaps
    }

    assert "ORPHAN_REFUND" in gap_types


# =========================================================
# TEST: PERFECTLY MATCHED DATA
# =========================================================

def test_no_gaps_for_perfect_matches():

    transaction_rows = []
    settlement_rows = []

    for i in range(50):

        txn_id = f"TXN{i:03d}"

        transaction_rows.append({
            "transaction_id": txn_id,
            "customer_id": f"CUST{i:03d}",
            "amount": 1000.00 + i,
            "currency": "INR",
            "transaction_date": "2026-03-15",
            "status": "SUCCESS",
        })

        settlement_rows.append({
            "settlement_id": f"SET{i:03d}",
            "transaction_id": txn_id,
            "settled_amount": 1000.00 + i,
            "settlement_date": "2026-03-16",
            "bank_reference": f"BNK{i:03d}",
        })

    transactions = pd.DataFrame(transaction_rows)

    settlements = pd.DataFrame(settlement_rows)

    gaps = detect_discrepancies(
        transactions,
        settlements,
    )

    assert gaps == []