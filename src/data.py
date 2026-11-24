"""Loading of the mock data (customers DB, FAQ)."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load_customers():
    return _load("customers.json")


def load_faq():
    return _load("faq.json")


def find_customer(email, customers):
    """Look a customer up by sender email (the 'database query' of the billing agent)."""
    email = (email or "").strip().lower()
    for c in customers:
        if c["email"].lower() == email:
            return c
    return None
