"""Synthetic financial dataset generator for demos."""
import random
from datetime import datetime, timedelta
import pandas as pd

VENDORS = [
    "Acme Corp", "GlobeTech Ltd", "Phoenix Logistics", "Nimbus Cloud Services",
    "Atlas Materials", "Vertex Consulting", "Quantum Systems", "Pinnacle Office Supplies",
    "Stellar Travel Co", "Bedrock Engineering", "Apex Marketing", "Halo Software",
]

# A "shady" vendor for fraud signals
SHADY_VENDOR = "Cascade Holdings LLC"

CATEGORIES = [
    "Office Supplies", "Software & Subscriptions", "Travel", "Consulting",
    "Marketing", "Equipment", "Utilities", "Maintenance", "Professional Services",
]


def generate_sample_invoices(n: int = 250, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic invoice data with intentional fraud signals."""
    rnd = random.Random(seed)
    start = datetime(2025, 1, 1)
    rows = []
    for i in range(n):
        vendor = rnd.choice(VENDORS)
        amount = round(rnd.uniform(50, 12000), 2)
        category = rnd.choice(CATEGORIES)
        date = start + timedelta(days=rnd.randint(0, 365))
        rows.append({
            "invoice_id": f"INV-{10000 + i}",
            "date": date.strftime("%Y-%m-%d"),
            "vendor": vendor,
            "amount": amount,
            "category": category,
            "approved_by": rnd.choice(["alice@corp.com", "bob@corp.com", "carol@corp.com", "dan@corp.com"]),
            "department": rnd.choice(["Finance", "Engineering", "Sales", "Operations", "HR"]),
        })

    # Inject fraud signals:
    # 1. Duplicate invoices (same vendor + amount + close dates)
    for j in range(5):
        base = rows[j * 10]
        dup = base.copy()
        dup["invoice_id"] = f"INV-DUP-{j}"
        dup["date"] = base["date"]
        rows.append(dup)

    # 2. Round-number splitting (just below approval thresholds)
    for j in range(8):
        rows.append({
            "invoice_id": f"INV-SPLIT-{j}",
            "date": (start + timedelta(days=rnd.randint(0, 365))).strftime("%Y-%m-%d"),
            "vendor": SHADY_VENDOR,
            "amount": 9999.00,
            "category": "Consulting",
            "approved_by": "dan@corp.com",
            "department": "Operations",
        })

    # 3. Outliers (very high amounts)
    for j in range(3):
        rows.append({
            "invoice_id": f"INV-BIG-{j}",
            "date": (start + timedelta(days=rnd.randint(0, 365))).strftime("%Y-%m-%d"),
            "vendor": SHADY_VENDOR,
            "amount": round(rnd.uniform(80000, 250000), 2),
            "category": "Professional Services",
            "approved_by": "dan@corp.com",
            "department": "Operations",
        })

    rnd.shuffle(rows)
    return pd.DataFrame(rows)


def generate_sample_csv_bytes(n: int = 250) -> bytes:
    df = generate_sample_invoices(n)
    return df.to_csv(index=False).encode("utf-8")
