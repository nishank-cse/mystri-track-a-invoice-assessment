# Verification Evidence

## Starter defects reproduced before repair

These observations were run against an untouched extraction of the supplied Track A starter.

| Case | Starter observation | Impact |
|---|---|---|
| Payment matching | `MAPLE / NOT-AN-INVOICE / 1250.00` imported and attached to invoice ID 1 because the amount matched. | A payment could alter the wrong customer's invoice. |
| Status filter | `open` returned `INV-101`; `paid` also returned `INV-101`. | The two views were not mutually correct. |
| Invalid data row | A mixed invoice CSV raised `Unknown customer_id` during normalization before processing later rows. | One bad row prevented valid rows from being imported. |
| Invoice retry | Re-importing `HARBOR / INV-100 / 1250.00` reported `imported`; changing its amount also reported `imported`. | Retries could create duplicate identities and changed records. |
| Money | `10.10 - (0.10 + 0.20)` produced a balance represented as `9.799999999999999`; export truncated it to `9.79`. | Screen/export values could disagree at cent precision. |

## Passing-after regression checks

Command:

```text
python -m unittest discover -s tests -v
```

Result: **15 tests passed**.

Important checks include:

- exact customer + invoice identity for payment matching;
- identical invoice/payment retries are skipped;
- changed invoice/payment identities are rejected;
- valid rows survive an invalid row;
- `open` and `paid` filters contain only their respective records;
- 0.10 + 0.20 is reported as 0.30;
- overpayment gives a negative balance and `paid`;
- exports use two decimal places;
- original fixture records and payment allocations are preserved.

## Existing-register and restart check

After:

```text
python restore_fixture.py --replace
```

the API reported:

```text
9 invoices, 5 payments
open invoices: 7
outstanding: INR 3698.19
unmatched: KEEP-U1 / MAPLE / WAIT-900 / INR 33.33
```

I then imported:

```csv
customer_id,invoice_number,amount,due_date
HARBOR,NEW-900,12.34,2026-09-20
BAD,BAD-1,9.99,2026-09-20
```

Expected before running: one valid invoice imported and the invalid customer row rejected.

Observed:

```json
{"imported": 1, "skipped": 0, "rejected": 1,
 "errors": [{"line": 3, "reason": "Unknown customer_id"}]}
```

Then payment `NEW-P1` for `HARBOR / NEW-900 / 12.34` was imported. After restarting the HTTP server, `NEW-900` remained paid with balance `0.0`, while original `KEEP-700` remained at `400.0` outstanding. The overall outstanding total remained `3698.19`.

## Additional improvement

The export endpoint now accepts `status=all|open|paid`, and the browser updates the export link to follow the selected register view. This was checked through the API and regression test.

## Known limits

The browser JavaScript was checked with `node --check`; HTTP/API behaviour was tested locally. No full browser automation was used. The task does not require concurrency or production deployment, so those remain untested.
