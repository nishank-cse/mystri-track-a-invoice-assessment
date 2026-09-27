import csv
import io
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal('0.01')


def money_decimal(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def invoices(db, status='all'):
    if status not in ('all', 'open', 'paid'):
        raise ValueError('status must be all, open or paid')
    rows = db.execute('''
        SELECT i.id, i.customer_id, c.name AS customer_name, i.invoice_number,
               i.amount, i.due_date
        FROM invoices i JOIN customers c ON c.customer_id=i.customer_id
        ORDER BY i.id
    ''').fetchall()
    result = []
    for row in rows:
        item = dict(row)
        paid = sum(
            (money_decimal(p['amount']) for p in db.execute(
                'SELECT amount FROM payments WHERE invoice_id=?', (row['id'],)
            ).fetchall()),
            Decimal('0.00')
        )
        amount = money_decimal(item['amount'])
        balance = amount - paid
        item['amount'] = float(amount)
        item['paid'] = float(paid)
        item['balance'] = float(balance)
        item['status'] = 'paid' if balance <= 0 else 'open'
        result.append(item)
    if status != 'all':
        result = [r for r in result if r['status'] == status]
    return result


def overview(db):
    rows = invoices(db)
    unmatched = [dict(r) for r in db.execute('''SELECT payment_id, customer_id,
        invoice_number, amount FROM payments WHERE invoice_id IS NULL ORDER BY payment_id''')]
    return {'invoices': rows, 'unmatched_payments': unmatched, 'summary': {
        'invoice_count': len(rows),
        'open_count': sum(r['status'] == 'open' for r in rows),
        'outstanding': round(sum(max(0, r['balance']) for r in rows), 2),
    }}


def export_csv(db, status='all'):
    output = io.StringIO(newline='')
    fields = ['customer_id', 'invoice_number', 'amount', 'paid', 'balance', 'status']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in invoices(db, status):
        item = {k: row[k] for k in fields}
        for key in ('amount', 'paid', 'balance'):
            item[key] = f"{money_decimal(item[key]):.2f}"
        writer.writerow(item)
    return output.getvalue()
