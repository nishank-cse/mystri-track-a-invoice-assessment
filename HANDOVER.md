# Handover

- Name: Nishank Mukhija
- Email used for this application: nishankmukhija.cse@gmail.com
- Chosen track: A
- Why this track: I chose Product Engineering because the task is a focused software reliability exercise involving debugging, API behaviour, persistence and verification.
- Approximate total time: 3 hours 30 minutes

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

I repaired the highest-impact correctness issues:

- Payments now match only by `(customer_id, invoice_number)`.
- Invoice identity is idempotent and rejects changed duplicates.
- Invalid CSV rows are isolated so valid rows can still be imported.
- Status filters are correct.
- Money calculations use decimal-cent arithmetic.
- CSV exports round money values to two decimal places.
- The browser checks HTTP responses and displays actual import counts and errors.

The additional improvement is filtered CSV export: the export follows the selected All/Open/Paid view.

## Evidence and limits

I reproduced the starter defects against the untouched pack, then reran the repaired regression suite and a fixture-backed API lifecycle.

The existing register remained at:

- 9 invoices
- 5 payments
- INR 3,698.19 outstanding
- 1 unmatched payment

A new invoice/payment also survived a simulated application restart.

I added a new invoice `NEW-900` plus a payment and verified that the invoice became paid after restart.

I also tested a mixed import containing one unknown customer and two valid rows. The result was 2 imported and 1 rejected, with line 3 reported.

No schema migration was needed.

Known limitation: the application still uses SQLite REAL storage internally; calculations are normalized to decimal cents at the reporting boundary.

The browser was syntax-checked with Node and API behaviour was exercised locally. I did not use a full browser automation suite.

A real-project follow-up would be checking concurrent writers and whether SQLite is still appropriate as usage grows.

## Tools and judgment

- ChatGPT (GPT-5.6 Luna) was used for code investigation, debugging suggestions and regression-test design. I independently verified the suggestions against the supplied business rules and local test results.
- One concrete example: ChatGPT suggested identity-based payment matching. I reproduced the incorrect amount-only matching behaviour and verified the corrected `(customer_id, invoice_number)` matching with a regression test.
- ChatGPT suggested Decimal-based reporting. I kept the existing storage schema to avoid unnecessary migration risk and verified cent arithmetic plus overpayment behaviour.
- Python `unittest` and a local HTTP server were used to verify persistence, imports and restart behaviour.
- Node `--check` was used to verify the browser JavaScript syntax.

## Questions I would investigate in a real project

- What concurrency level and number of simultaneous users should the application support?
- Should SQLite remain the production database as usage grows?
- Should payment imports support additional payment-provider reference IDs for stronger idempotency?
- What authentication and authorization requirements apply to invoice and payment data?
- What audit-log and data-retention requirements apply to financial changes?
