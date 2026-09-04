# Revenue Recovery Agent — Day 1

## How to run this

1. Put `database.py`, `generate_data.py`, `app.py`, and `requirements.txt` all in the
   same folder (the one you opened in VS Code).
2. Open a terminal in that folder and set up your environment:

   ```
   python -m venv venv
   ```

   Activate it:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

3. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the app:

   ```
   streamlit run app.py
   ```

5. Your browser should open automatically to `localhost:8501`. If not, copy the
   URL shown in the terminal into your browser.

6. Click **"Generate fresh test data"** in the sidebar. You should immediately see
   KPI cards, a payments table, and a failed-payments tab fill up with fake data.

## What's here today

- `database.py` — sets up a local SQLite database (`payments.db`, created
  automatically) with a `payments` table and an `audit_log` table (for later).
- `generate_data.py` — creates 50 realistic fake payments, ~40% of them failed,
  with believable failure reasons.
- `app.py` — the dashboard: KPI cards, tabs for all payments / failed payments /
  audit log.

## What's next

- **Day 2:** tighten up failure detection (right now "failed" status *is* the
  detection — Day 2 adds things like retry eligibility and days-since-failure).
- **Day 3:** wire in the Claude API so each failed payment gets a real decision
  (retry / remind / stop), and log every decision into the audit log.
- **Day 4:** add the stopping rule (max 3 retries), and a results summary
  showing money recovered.
