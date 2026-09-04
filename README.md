# 💰 AI Revenue Recovery Agent

An AI-powered payment recovery system that detects failed payments, evaluates recovery opportunities, chooses the best recovery action, and tracks recovered revenue automatically.

Built as a hackathon project using Python, Streamlit, SQLite, and OpenRouter AI.

---

## 🚀 What the Project Does

Failed payments can result in significant lost revenue.

The AI Revenue Recovery Agent automatically:

1. Detects failed payments
2. Analyzes payment information and failure reasons
3. Calculates how long the payment has been failing
4. Classifies payment urgency
5. Checks whether the payment is eligible for recovery
6. Uses AI to choose one action:
   - **RETRY** — attempt the payment again
   - **REMIND** — ask the customer to fix their payment method
   - **STOP** — stop further recovery attempts
7. Simulates the retry outcome
8. Updates recovered revenue
9. Records every AI decision in an audit log
10. Prevents unlimited recovery attempts

---

## 🧠 AI Decision Engine

For every eligible failed payment, the AI considers:

- Customer
- Payment amount
- Failure reason
- Days since failure
- Urgency
- Previous retry count
- Recovery attempt count
- Payment eligibility

The AI returns a structured decision:

```text
RETRY
REMIND
STOP