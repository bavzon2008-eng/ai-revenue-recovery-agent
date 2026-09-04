from datetime import datetime

MAX_RETRIES = 3


def days_since(created_at_iso):
    """How many days ago this payment failed."""
    created = datetime.fromisoformat(created_at_iso)
    delta = datetime.now() - created
    return delta.days


def is_eligible_for_action(payment):
    """A failed payment is worth acting on if we haven't already given up on it."""
    return payment["retry_count"] < MAX_RETRIES and payment["recovered"] == 0


def classify_urgency(payment):
    """
    Simple urgency label based on how long it's been failing and how much money
    is involved. This is what the AI agent will use on Day 3 to help decide
    what action to take.
    """
    age = days_since(payment["created_at"])
    amount = payment["amount"]

    if age >= 5 or amount >= 3000:
        return "high"
    elif age >= 2:
        return "medium"
    else:
        return "low"


def enrich_failed_payments(failed_payments):
    """
    Takes the raw failed payments from the database and adds the extra fields
    the recovery agent needs: age in days, urgency, and whether it's still
    eligible for action.
    """
    enriched = []
    for p in failed_payments:
        p = dict(p)  # don't mutate the original
        p["days_failed"] = days_since(p["created_at"])
        p["urgency"] = classify_urgency(p)
        p["eligible"] = is_eligible_for_action(p)
        enriched.append(p)
    return enriched
