from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict, Counter
from datetime import datetime
from decimal import Decimal
import os
import csv

app = FastAPI(title="Payments Reconciliation API")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TRANSACTIONS_PATH = os.path.join(BASE_DIR, "src/data", "transactions.csv")
SETTLEMENTS_PATH  = os.path.join(BASE_DIR, "src/data", "settlements.csv")

# ---------------------------------------------------
# CORS
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# GLOBAL DATA STORE
# ---------------------------------------------------
transactions = []
settlements = []

transactions_by_id = {}
settlements_by_txn = defaultdict(list)

# ---------------------------------------------------
# LOAD CSV FILES
# ---------------------------------------------------
def load_transactions():
    data = []


    with open(TRANSACTIONS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["amount"] = Decimal(row["amount"])
            row["transaction_timestamp"] = datetime.strptime(
                row["transaction_timestamp"],
                "%Y-%m-%d %H:%M:%S"
            )

            data.append(row)

    return data


def load_settlements():
    data = []

    with open(SETTLEMENTS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["settled_amount"] = Decimal(row["settled_amount"])
            row["settlement_timestamp"] = datetime.strptime(
                row["settlement_timestamp"],
                "%Y-%m-%d %H:%M:%S"
            )

            data.append(row)

    return data


# ---------------------------------------------------
# STARTUP EVENT
# ---------------------------------------------------
@app.on_event("startup")
def startup_event():
    global transactions
    global settlements
    global transactions_by_id
    global settlements_by_txn

    transactions = load_transactions()
    settlements = load_settlements()

    transactions_by_id = {
        txn["transaction_id"]: txn
        for txn in transactions
    }

    settlements_by_txn = defaultdict(list)

    for settlement in settlements:
        settlements_by_txn[
            settlement["transaction_id"]
        ].append(settlement)

    print("CSV files loaded successfully")


# ---------------------------------------------------
# GAP DETECTION
# ---------------------------------------------------
def detect_late_settlements():
    """
    Transaction happened in March
    but settlement occurred in April.
    """

    gaps = []

    for settlement in settlements:
        txn_id = settlement["transaction_id"]

        txn = transactions_by_id.get(txn_id)

        if not txn:
            continue

        txn_month = txn["transaction_timestamp"].month
        settlement_month = settlement["settlement_timestamp"].month

        if txn_month == 3 and settlement_month == 4:
            gaps.append({
                "transaction_id": txn_id,
                "transaction_timestamp": txn["transaction_timestamp"],
                "settlement_timestamp": settlement["settlement_timestamp"],
                "amount": str(txn["amount"]),
            })

    return gaps


def detect_rounding_diffs():
    """
    Detect amount mismatches <= 0.05
    """

    gaps = []

    for txn_id, txn in transactions_by_id.items():
        txn_amount = txn["amount"]

        related_settlements = settlements_by_txn.get(txn_id, [])

        for settlement in related_settlements:
            settlement_amount = settlement["settled_amount"]

            diff = abs(txn_amount - settlement_amount)

            if diff > Decimal("0.00") and diff <= Decimal("0.05"):
                gaps.append({
                    "transaction_id": txn_id,
                    "transaction_amount": str(txn_amount),
                    "settlement_amount": str(settlement_amount),
                    "difference": str(diff),
                })

    return gaps


def detect_duplicate_settlements():
    """
    Same transaction settled more than once.
    """

    gaps = []

    for txn_id, related_settlements in settlements_by_txn.items():

        if len(related_settlements) > 1:

            unique_entries = Counter(
                (
                    s["settled_amount"],
                    s["settlement_timestamp"],
                )
                for s in related_settlements
            )

            for key, count in unique_entries.items():

                if count > 1:
                    gaps.append({
                        "transaction_id": txn_id,
                        "duplicate_count": count,
                        "settled_amount": str(key[0]),
                        "settlement_timestamp": key[1],
                    })

    return gaps


def detect_orphan_refunds():
    """
    Refund exists but original transaction does not exist.
    """

    gaps = []

    for settlement in settlements:

        amount = settlement["settled_amount"]
        txn_id = settlement["transaction_id"]

        if amount < 0:

            if txn_id not in transactions_by_id:
                gaps.append({
                    "transaction_id": txn_id,
                    "refund_amount": str(amount),
                    "settlement_timestamp": settlement["settlement_timestamp"],
                    "bank_reference": settlement["bank_reference"],
                })

    return gaps


# ---------------------------------------------------
# SUMMARY ENDPOINT
# ---------------------------------------------------
@app.get("/summary")
def summary():

    total_transactions = len(transactions)
    total_settlements = len(settlements)

    transaction_sum = sum(
        txn["amount"]
        for txn in transactions
    )

    settlement_sum = sum(
        settlement["settled_amount"]
        for settlement in settlements
    )

    return {
        "total_transactions": total_transactions,
        "total_settlements": total_settlements,
        "transaction_total_amount": str(transaction_sum),
        "settlement_total_amount": str(settlement_sum),
        "net_difference": str(transaction_sum - settlement_sum),

        "gap_summary": {
            "late_settlements": len(detect_late_settlements()),
            "rounding_differences": len(detect_rounding_diffs()),
            "duplicate_settlements": len(detect_duplicate_settlements()),
            "orphan_refunds": len(detect_orphan_refunds()),
        }
    }


# ---------------------------------------------------
# GAPS ENDPOINT
# ---------------------------------------------------
@app.get("/gaps")
def gaps():

    return {
        "late_settlements": detect_late_settlements(),
        "rounding_differences": detect_rounding_diffs(),
        "duplicate_settlements": detect_duplicate_settlements(),
        "orphan_refunds": detect_orphan_refunds(),
    }


# ---------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Payments Reconciliation API Running"
    }


# ---------------------------------------------------
# RUN
# ---------------------------------------------------
# uvicorn main:app --reload