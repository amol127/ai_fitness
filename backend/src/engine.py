# engine.py

"""
Payments Reconciliation Engine

This module detects reconciliation gaps between:
1. Platform transactions
2. Bank settlements

Supported gap types:
- LATE_SETTLEMENT
- ROUNDING_DIFFERENCE
- DUPLICATE_SETTLEMENT
- ORPHAN_REFUND
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Dict, List

import pandas as pd


# =========================================================
# CONSTANTS
# =========================================================

LATE_SETTLEMENT = "LATE_SETTLEMENT"
ROUNDING_DIFFERENCE = "ROUNDING_DIFFERENCE"
DUPLICATE_SETTLEMENT = "DUPLICATE_SETTLEMENT"
ORPHAN_REFUND = "ORPHAN_REFUND"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _round(value):
    """
    Safely round float values to 2 decimal places.
    Returns None if value is None.
    """

    if value is None:
        return None

    return round(float(value), 2)


def _safe_date(value):
    """
    Convert pandas Timestamp/date to YYYY-MM-DD string.
    Returns None if missing.
    """

    if pd.isna(value):
        return None

    return pd.to_datetime(value).strftime("%Y-%m-%d")


# =========================================================
# GAP DETECTION
# =========================================================

def detect_discrepancies(
    transactions: pd.DataFrame,
    settlements: pd.DataFrame,
) -> List[Dict]:
    """
    Detect reconciliation discrepancies between transactions
    and settlements.

    Detects exactly these gap types:
    - LATE_SETTLEMENT
    - ROUNDING_DIFFERENCE
    - DUPLICATE_SETTLEMENT
    - ORPHAN_REFUND

    Parameters
    ----------
    transactions : pd.DataFrame
        Platform transaction records.

    settlements : pd.DataFrame
        Bank settlement records.

    Returns
    -------
    List[Dict]
        List of structured discrepancy dictionaries.
    """

    discrepancies: List[Dict] = []

    # -----------------------------------------------------
    # COPY DATAFRAMES
    # Avoid mutating original inputs
    # -----------------------------------------------------
    txns = transactions.copy()
    stls = settlements.copy()

    # -----------------------------------------------------
    # DATE CONVERSION
    # -----------------------------------------------------
    txns["transaction_date"] = pd.to_datetime(
        txns["transaction_date"]
    )

    stls["settlement_date"] = pd.to_datetime(
        stls["settlement_date"]
    )

    # -----------------------------------------------------
    # FAST LOOKUP MAP
    # -----------------------------------------------------
    txn_lookup = txns.set_index("transaction_id").to_dict("index")

    # =====================================================
    # 1. LATE_SETTLEMENT
    # =====================================================
    late_settlements = stls.merge(
        txns,
        on="transaction_id",
        how="inner",
        suffixes=("_settlement", "_transaction")
    )

    late_mask = (
        (late_settlements["transaction_date"].dt.month == 3)
        &
        (late_settlements["transaction_date"].dt.year == 2026)
        &
        (
            late_settlements["settlement_date"]
            >= pd.Timestamp("2026-04-01")
        )
    )

    for _, row in late_settlements[late_mask].iterrows():

        discrepancies.append({
            "gap_type": LATE_SETTLEMENT,
            "transaction_id": row["transaction_id"],
            "transaction_amount": _round(row["amount"]),
            "settled_amount": _round(row["settled_amount"]),
            "transaction_date": _safe_date(
                row["transaction_date"]
            ),
            "settlement_date": _safe_date(
                row["settlement_date"]
            ),
            "difference": _round(
                row["amount"] - row["settled_amount"]
            ),
            "description": (
                "Transaction occurred in March 2026 "
                "but settlement happened after month-end."
            ),
        })

    # =====================================================
    # 2. ROUNDING_DIFFERENCE
    # =====================================================
    rounding_df = stls.merge(
        txns,
        on="transaction_id",
        how="inner",
        suffixes=("_settlement", "_transaction")
    )

    rounding_df["difference"] = (
        rounding_df["amount"]
        - rounding_df["settled_amount"]
    ).abs()

    rounding_mask = (
        (rounding_df["difference"] >= 0.001)
        &
        (rounding_df["difference"] <= 0.009)
    )

    for _, row in rounding_df[rounding_mask].iterrows():

        discrepancies.append({
            "gap_type": ROUNDING_DIFFERENCE,
            "transaction_id": row["transaction_id"],
            "transaction_amount": _round(row["amount"]),
            "settled_amount": _round(row["settled_amount"]),
            "transaction_date": _safe_date(
                row["transaction_date"]
            ),
            "settlement_date": _safe_date(
                row["settlement_date"]
            ),
            "difference": _round(row["difference"]),
            "description": (
                "Minor rounding variance detected between "
                "transaction and settlement amounts."
            ),
        })

    # =====================================================
    # 3. DUPLICATE_SETTLEMENT
    # =====================================================
    duplicate_counts = (
        stls["transaction_id"]
        .value_counts()
    )

    duplicate_txn_ids = duplicate_counts[
        duplicate_counts > 1
    ].index.tolist()

    for txn_id in duplicate_txn_ids:

        duplicate_rows = stls[
            stls["transaction_id"] == txn_id
        ]

        txn = txn_lookup.get(txn_id)

        for _, row in duplicate_rows.iterrows():

            discrepancies.append({
                "gap_type": DUPLICATE_SETTLEMENT,
                "transaction_id": txn_id,
                "transaction_amount": (
                    _round(txn["amount"])
                    if txn
                    else None
                ),
                "settled_amount": _round(
                    row["settled_amount"]
                ),
                "transaction_date": (
                    _safe_date(txn["transaction_date"])
                    if txn
                    else None
                ),
                "settlement_date": _safe_date(
                    row["settlement_date"]
                ),
                "difference": 0.00,
                "description": (
                    "Multiple settlement records found "
                    "for the same transaction_id."
                ),
            })

    # =====================================================
    # 4. ORPHAN_REFUND
    # =====================================================
    orphan_refunds = stls[
        (stls["settled_amount"] < 0)
        &
        (
            ~stls["transaction_id"].isin(
                txns["transaction_id"]
            )
        )
    ]

    for _, row in orphan_refunds.iterrows():

        discrepancies.append({
            "gap_type": ORPHAN_REFUND,
            "transaction_id": row["transaction_id"],
            "transaction_amount": None,
            "settled_amount": _round(
                row["settled_amount"]
            ),
            "transaction_date": None,
            "settlement_date": _safe_date(
                row["settlement_date"]
            ),
            "difference": _round(
                abs(row["settled_amount"])
            ),
            "description": (
                "Refund settlement exists without a "
                "matching original transaction."
            ),
        })

    return discrepancies


# =========================================================
# SUMMARY
# =========================================================

def get_summary(
    transactions: pd.DataFrame,
    settlements: pd.DataFrame,
    discrepancies: List[Dict],
) -> Dict:
    """
    Generate reconciliation summary statistics.

    Parameters
    ----------
    transactions : pd.DataFrame
        Platform transaction records.

    settlements : pd.DataFrame
        Bank settlement records.

    discrepancies : List[Dict]
        Output from detect_discrepancies().

    Returns
    -------
    Dict
        Structured reconciliation summary.
    """

    txns = transactions.copy()
    stls = settlements.copy()

    matched_count = stls[
        stls["transaction_id"].isin(
            txns["transaction_id"]
        )
    ]["transaction_id"].nunique()

    unmatched_count = len(
        stls[
            ~stls["transaction_id"].isin(
                txns["transaction_id"]
            )
        ]
    )

    total_transaction_amount = (
        txns["amount"].sum()
    )

    total_settled_amount = (
        stls["settled_amount"].sum()
    )

    gap_counter = Counter(
        gap["gap_type"]
        for gap in discrepancies
    )

    return {
        "total_transactions": int(len(txns)),
        "total_settlements": int(len(stls)),
        "matched_count": int(matched_count),
        "unmatched_count": int(unmatched_count),

        "total_transaction_amount": _round(
            total_transaction_amount
        ),

        "total_settled_amount": _round(
            total_settled_amount
        ),

        "net_difference": _round(
            total_transaction_amount
            - total_settled_amount
        ),

        "gaps_by_type": {
            LATE_SETTLEMENT: gap_counter.get(
                LATE_SETTLEMENT,
                0,
            ),
            ROUNDING_DIFFERENCE: gap_counter.get(
                ROUNDING_DIFFERENCE,
                0,
            ),
            DUPLICATE_SETTLEMENT: gap_counter.get(
                DUPLICATE_SETTLEMENT,
                0,
            ),
            ORPHAN_REFUND: gap_counter.get(
                ORPHAN_REFUND,
                0,
            ),
        },
    }


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    transactions_df = pd.read_csv(
        "data/transactions.csv"
    )

    settlements_df = pd.read_csv(
        "data/settlements.csv"
    )

    discrepancies = detect_discrepancies(
        transactions_df,
        settlements_df,
    )

    summary = get_summary(
        transactions_df,
        settlements_df,
        discrepancies,
    )

    print("\n========== SUMMARY ==========\n")

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    print("\n======= DISCREPANCIES =======\n")

    print(
        json.dumps(
            discrepancies,
            indent=2,
        )
    )