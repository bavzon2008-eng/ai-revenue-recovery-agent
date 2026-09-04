import random
from datetime import datetime, timedelta

from database import init_db, insert_payment, clear_all

CUSTOMER_NAMES = [
    "Ananya Rao", "Vikram Singh", "Priya Nair", "Rahul Mehta", "Sneha Iyer",
    "Arjun Kapoor", "Divya Menon", "Karan Malhotra", "Neha Gupta", "Rohan Das",
    "Ishita Shah", "Aditya Verma", "Meera Pillai", "Siddharth Rao", "Kavya Reddy",
]

FAILURE_REASONS = [
    "insufficient_funds",
    "card_declined",
    "network_timeout",
    "bank_server_error",
    "expired_card",
]


def generate_fake_payments(n=50, failure_rate=0.4):
    """Creates n fake payment records, with failure_rate fraction of them failed."""
    init_db()
    clear_all()
    now = datetime.now()

    for _ in range(n):
        name = random.choice(CUSTOMER_NAMES)
        amount = round(random.uniform(199, 4999), 2)
        created_at = (
            now - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23))
        ).isoformat()

        if random.random() < failure_rate:
            status = "failed"
            reason = random.choice(FAILURE_REASONS)
        else:
            status = "success"
            reason = None

        insert_payment(name, amount, status, reason, created_at)

    print(f"Generated {n} fake payments ({int(n * failure_rate)} approx. failed).")


if __name__ == "__main__":
    generate_fake_payments()
