import json
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from dotenv import load_dotenv

from database import (
    get_failed_payments,
    update_payment,
    log_action,
)
from detection import enrich_failed_payments


load_dotenv()

MODEL = "google/gemma-4-31b-it:free"

FALLBACK_MODELS = [
    "minimax/minimax-m3:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]
MAX_RECOVERY_ATTEMPTS = 3


def get_client():
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. "
            "Make sure your .env file contains your OpenRouter API key."
        )

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def clean_json_response(text):
    """
    Clean the model response and extract JSON.
    Free models sometimes return markdown or extra text.
    """

    if not text:
        raise ValueError("AI returned an empty response.")

    text = text.strip()

    # Remove markdown code fences.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    text = text.strip()

    # Find the first JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"AI did not return valid JSON. Response was: {text[:300]}"
        )

    return text[start:end + 1]


def ask_ai(payment):
    """
    Ask OpenRouter to choose a recovery action.
    """

    client = get_client()

    prompt = f"""
You are a payment recovery agent.

Choose ONE action:

RETRY
REMIND
STOP

Payment:
Customer: {payment["customer_name"]}
Amount: ₹{payment["amount"]:.2f}
Failure reason: {payment["failure_reason"]}
Days failed: {payment["days_failed"]}
Urgency: {payment["urgency"]}
Previous retries: {payment["retry_count"]}
Eligible: {payment["eligible"]}

Rules:

- If Eligible is false, choose STOP.
- Never exceed 3 retries.
- Temporary failures such as network_timeout or bank_server_error can usually be RETRY.
- insufficient_funds or card_declined may require a REMIND.
- Consider urgency, amount, failure reason and retry count.
- STOP means no further recovery attempt.
- RETRY means simulate another payment attempt.
- REMIND means ask the customer to fix their payment method.

Return ONLY this JSON:

{{"action":"RETRY","reason":"Temporary failure may recover on another attempt","confidence":0.85}}

The action MUST be exactly RETRY, REMIND, or STOP.

Confidence MUST be a number from 0 to 1.

Do not use markdown.
Do not add explanations outside the JSON.
"""

    response = client.chat.completions.create(
    model=MODEL,
    extra_body={
        "models": FALLBACK_MODELS,
    },
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    max_tokens=250,
    temperature=0.1,
)

    message = response.choices[0].message

    # Some free models may return no content.
    raw_text = message.content

    if not raw_text:
        raise ValueError(
            "AI returned an empty response."
        )

    json_text = clean_json_response(raw_text)

    try:
        result = json.loads(json_text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"AI returned malformed JSON: {exc}"
        )

    action = str(
        result.get("action", "")
    ).upper().strip()

    if action not in {
        "RETRY",
        "REMIND",
        "STOP",
    }:
        raise ValueError(
            f"Invalid AI action: {action}"
        )

    try:
        confidence = float(
            result.get("confidence", 0)
        )
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    reason = result.get(
        "reason",
        "No reason provided",
    )

    if not isinstance(reason, str):
        reason = str(reason)

    return {
        "action": action,
        "reason": reason,
        "confidence": confidence,
    }


def simulate_retry(payment):
    """
    Simulate a payment retry.

    This is NOT a real payment.
    It is only for the hackathon demonstration.
    """

    recoverable_reasons = {
        "insufficient_funds",
        "network_timeout",
        "bank_server_error",
    }

    if payment["failure_reason"] in recoverable_reasons:
        recovery_score = 0.70
    else:
        recovery_score = 0.35

    return (
        payment["id"] % 10
    ) < int(recovery_score * 10)


def get_ai_decision(payment):
    if (
        not payment["eligible"]
        or payment.get("recovery_attempts", 0) >= MAX_RECOVERY_ATTEMPTS
    ):
        return {
            "action": "STOP",
            "reason": (
                "Maximum recovery attempts reached "
                "or payment is no longer eligible."
            ),
            "confidence": 1.0,
        }

    try:
        return ask_ai(payment)
    except Exception as exc:
        return {
            "action": "STOP",
            "reason": f"AI temporarily failed: {exc}",
            "confidence": 0.0,
        }


def run_recovery_batch():
    failed_payments = get_failed_payments()
    enriched = enrich_failed_payments(failed_payments)

    results = {
        "processed": 0,
        "recovered_count": 0,
        "recovered_amount": 0.0,
        "actions": [],
    }

    # Run AI decisions in parallel to reduce waiting time.
    # Database updates remain sequential for safety.
    with ThreadPoolExecutor(max_workers=5) as executor:
        decisions = list(
            executor.map(get_ai_decision, enriched)
        )

    for payment, decision in zip(enriched, decisions):
        recovery_attempts = payment.get("recovery_attempts", 0)

        action = decision["action"]
        recovered = False

        # Count every recovery cycle.
        update_payment(
            payment["id"],
            recovery_attempts=recovery_attempts + 1,
        )

        if action == "RETRY":
            new_retry_count = payment["retry_count"] + 1

            update_payment(
                payment["id"],
                retry_count=new_retry_count,
            )

            recovered = simulate_retry(payment)

            if recovered:
                update_payment(
                    payment["id"],
                    status="success",
                    recovered=1,
                )

            details = (
                f"AI chose RETRY. "
                f"Reason: {decision['reason']} "
                f"Confidence: {decision['confidence']:.2f}. "
                f"Simulated retry "
                f"{'succeeded' if recovered else 'failed'}."
            )

        elif action == "REMIND":
            details = (
                f"AI chose REMIND. "
                f"Reason: {decision['reason']} "
                f"Confidence: {decision['confidence']:.2f}."
            )

        else:
            details = (
                f"AI chose STOP. "
                f"Reason: {decision['reason']} "
                f"Confidence: {decision['confidence']:.2f}."
            )

        log_action(
            payment["id"],
            action,
            details,
            datetime.now().isoformat(),
        )

        results["processed"] += 1

        if recovered:
            results["recovered_count"] += 1
            results["recovered_amount"] += payment["amount"]

        results["actions"].append(
            {
                "payment_id": payment["id"],
                "customer": payment["customer_name"],
                "amount": payment["amount"],
                "action": action,
                "reason": decision["reason"],
                "confidence": round(decision["confidence"], 2),
                "recovered": "Yes" if recovered else "No",
            }
        )

    return results