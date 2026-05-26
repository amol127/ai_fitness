import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)
os.makedirs("src/data", exist_ok=True)
# -----------------------------
# CONFIG
# -----------------------------
TOTAL_MATCHED_ROWS = 50

TRANSACTIONS_FILE = "src/data/transactions.csv"
SETTLEMENTS_FILE = "src/data/settlements.csv"

MERCHANTS = [
    "Amazon",
    "Flipkart",
    "Swiggy",
    "Zomato",
    "Myntra",
    "Uber",
    "BookMyShow",
    "Nykaa",
]

PAYMENT_METHODS = [
    "UPI",
    "CARD",
    "NETBANKING",
    "WALLET",
]

STATUS = "SUCCESS"

# -----------------------------
# HELPERS
# -----------------------------
def random_timestamp_march():
    start = datetime(2026, 3, 1, 0, 0, 0)
    end = datetime(2026, 3, 31, 23, 59, 59)

    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))

    return start + timedelta(seconds=random_seconds)


def settlement_timestamp(txn_time):
    # Typical T+0 / T+1 settlement
    offset_hours = random.randint(2, 30)
    return txn_time + timedelta(hours=offset_hours)


def generate_txn_id(i):
    return f"TXN202603{i:05d}"


def generate_settlement_id(i):
    return f"SET202603{i:05d}"


def random_amount():
    return round(random.uniform(100, 5000), 2)


# -----------------------------
# DATA HOLDERS
# -----------------------------
transactions = []
settlements = []

# -----------------------------
# 1. NORMAL MATCHED ROWS (50)
# -----------------------------
for i in range(1, TOTAL_MATCHED_ROWS + 1):
    txn_id = generate_txn_id(i)
    settlement_id = generate_settlement_id(i)

    txn_time = random_timestamp_march()
    settle_time = settlement_timestamp(txn_time)

    amount = random_amount()

    txn_row = {
        "transaction_id": txn_id,
        "merchant": random.choice(MERCHANTS),
        "payment_method": random.choice(PAYMENT_METHODS),
        "amount": f"{amount:.2f}",
        "currency": "INR",
        "transaction_timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": STATUS,
    }

    settlement_row = {
        "settlement_id": settlement_id,
        "transaction_id": txn_id,
        "settled_amount": f"{amount:.2f}",
        "settlement_timestamp": settle_time.strftime("%Y-%m-%d %H:%M:%S"),
        "bank_reference": f"BNKREF{i:08d}",
    }

    transactions.append(txn_row)
    settlements.append(settlement_row)

# ---------------------------------------------------------
# GAP 1: TRANSACTION THAT SETTLED ON APRIL 1ST
# ---------------------------------------------------------
late_txn_id = "TXN20260390001"

transactions.append({
    "transaction_id": late_txn_id,
    "merchant": "Amazon",
    "payment_method": "UPI",
    "amount": "1899.50",
    "currency": "INR",
    "transaction_timestamp": "2026-03-31 22:45:12",
    "status": STATUS,
})

settlements.append({
    "settlement_id": "SET20260400001",
    "transaction_id": late_txn_id,
    "settled_amount": "1899.50",
    "settlement_timestamp": "2026-04-01 09:15:44",
    "bank_reference": "BNKREF90000001",
})

# ---------------------------------------------------------
# GAP 2: ROUNDING DIFFERENCE ONLY VISIBLE IN SUMS
# ---------------------------------------------------------
rounding_txn_id = "TXN20260390002"

transactions.append({
    "transaction_id": rounding_txn_id,
    "merchant": "Swiggy",
    "payment_method": "CARD",
    "amount": "1250.75",
    "currency": "INR",
    "transaction_timestamp": "2026-03-28 14:12:08",
    "status": STATUS,
})

# Settlement differs by 0.01
settlements.append({
    "settlement_id": "SET20260390002",
    "transaction_id": rounding_txn_id,
    "settled_amount": "1250.74",
    "settlement_timestamp": "2026-03-29 08:22:11",
    "bank_reference": "BNKREF90000002",
})

# ---------------------------------------------------------
# GAP 3: DUPLICATE SETTLEMENT ENTRY
# ---------------------------------------------------------
duplicate_txn_id = "TXN20260390003"

transactions.append({
    "transaction_id": duplicate_txn_id,
    "merchant": "Uber",
    "payment_method": "WALLET",
    "amount": "780.00",
    "currency": "INR",
    "transaction_timestamp": "2026-03-20 18:10:44",
    "status": STATUS,
})

duplicate_settlement = {
    "settlement_id": "SET20260390003",
    "transaction_id": duplicate_txn_id,
    "settled_amount": "780.00",
    "settlement_timestamp": "2026-03-21 07:30:10",
    "bank_reference": "BNKREF90000003",
}

# Insert duplicate twice
settlements.append(duplicate_settlement)
settlements.append(duplicate_settlement.copy())

# ---------------------------------------------------------
# GAP 4: REFUND WITH NO MATCHING ORIGINAL
# ---------------------------------------------------------
settlements.append({
    "settlement_id": "SET20260390004",
    "transaction_id": "RFND20260399999",
    "settled_amount": "-499.00",
    "settlement_timestamp": "2026-03-25 11:05:00",
    "bank_reference": "BNKREF90000004",
})

# -----------------------------
# SORT DATA
# -----------------------------
transactions.sort(key=lambda x: x["transaction_timestamp"])
settlements.sort(key=lambda x: x["settlement_timestamp"])

# -----------------------------
# WRITE TRANSACTIONS CSV
# -----------------------------
with open(TRANSACTIONS_FILE, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "transaction_id",
            "merchant",
            "payment_method",
            "amount",
            "currency",
            "transaction_timestamp",
            "status",
        ],
    )
    writer.writeheader()
    writer.writerows(transactions)

# -----------------------------
# WRITE SETTLEMENTS CSV
# -----------------------------
with open(SETTLEMENTS_FILE, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "settlement_id",
            "transaction_id",
            "settled_amount",
            "settlement_timestamp",
            "bank_reference",
        ],
    )
    writer.writeheader()
    writer.writerows(settlements)

print(f"Generated {TRANSACTIONS_FILE}")
print(f"Generated {SETTLEMENTS_FILE}")

print("\nInjected reconciliation gaps:")
print("1. Transaction settled on April 1st")
print("2. 0.01 rounding mismatch")
print("3. Duplicate settlement entry")
print("4. Refund without matching original transaction")