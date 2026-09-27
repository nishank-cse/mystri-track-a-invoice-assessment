# Handover

- Name: Nishank Mukhija
- Email used for this application: [ENTER THE EMAIL USED FOR THE APPLICATION]
- Chosen track: A
- Why this track: I chose Product Engineering because the task is a focused software reliability exercise involving debugging, API behaviour, persistence and verification.
- Approximate total time: [ENTER YOUR ACTUAL ELAPSED TIME; KEEP THIS WITHIN 4 HOURS]

## Run and verify

Prerequisite: Python 3.10+; no third-party packages.

```text
python -m unittest discover -s tests -v
python restore_fixture.py --replace
python app.py
```

Open `http://127.0.0.1:8787`.

The regression suite covers payment identity, invoice/payment retry semantics, row-level rejection, headers, money/overpayments, filters, export formatting and fixture preservation. `EVIDENCE.md` records before/after reproductions and clean-run checks.

## What I delivered

I repaired the highest-impact correctness issues: payments now match only by `(customer_id, invoice_number)`; invoice identity is idempotent and rejects changed duplicates; invalid rows are isolated; status filters are correct; money calculations use decimal-cent arithmetic; exports round to two decimals; and the browser checks HTTP responses and displays actual import counts/errors.

The additional improvement is **filtered CSV export**: the export follows the selected All/Open/Paid view.

## Evidence and limits

I reproduced the starter defects against the untouched pack, then reran the repaired regression suite and a fixture-backed API lifecycle. The existing register remained at 9 invoices, 5 payments, INR 3,698.19 outstanding and one unmatched payment; a new invoice/payment survived a simulated restart.

Changed-input case: I added a new invoice `NEW-900` plus a payment and expected the invoice to become paid after restart; that occurred. I also tested a mixed import with one unknown customer and two valid rows; the result was 2 imported / 1 rejected with line 3 reported.

No schema migration was needed. Known limit: the application still uses SQLite REAL storage internally; calculations are normalized to decimal cents at the reporting boundary. The browser was syntax-checked with Node and API behaviour was exercised locally; I did not use a full browser automation suite.

A real-project follow-up would be checking concurrent writers and whether SQLite is still appropriate as usage grows.

## Tools and judgment

- ChatGPT (GPT-5.6 Luna) suggested identity-based payment matching; I rejected amount-based matching after reproducing an incorrect attachment and verified the fix with a regression test.
- ChatGPT suggested Decimal-based reporting; I kept the existing storage schema to avoid unnecessary migration risk and verified cent arithmetic plus overpayment behaviour.
- Python `unittest` and a local HTTP server were used to verify persistence, imports and restart behaviour; Node `--check` verified the browser JavaScript syntax.
