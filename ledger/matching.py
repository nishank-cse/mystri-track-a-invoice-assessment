from .storage import invoice_by_key


def find_invoice(db, payment):
    # Invoice identity is the customer + invoice number pair.
    # Payment amount must never be used to infer identity.
    exact = invoice_by_key(db, payment['customer_id'], payment['invoice_number'])
    return exact['id'] if exact else None
