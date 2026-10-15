"""Snapshot-scoped evidence dossier; never infer balances, identities or account age."""
from decimal import Decimal, localcontext
from fintrace.contracts import AccountKey, content_id


def get_account_dossier(account_key, model, graph=None):
    account = account_key if isinstance(account_key, dict) else {"bank_id": account_key.bank_id, "account_id": account_key.account_id}
    AccountKey(**account)
    priority = model["priorities"].get(content_id(account))
    if priority is None:
        return None
    findings = [value for value in model["findings"].values() if account in value["subject_accounts"]]
    alerts = [value for value in model["alerts"] if value["subject"] == account]
    transactions = [row for row in (graph or {}).get("edges", []) if row["sender"] == account or row["receiver"] == account]
    totals = {}
    with localcontext() as context:
        context.prec = 60
        for row in transactions:
            direction = "paid" if row["sender"] == account else "received"
            currency = row["payment_currency"] if direction == "paid" else row["receiving_currency"]
            totals.setdefault(currency, {"paid": Decimal(0), "received": Decimal(0)})[direction] += Decimal(row["amount_" + direction])
    return {"account": account, "priority": priority, "findings": findings, "alerts": alerts,
            "transactions": sorted(transactions, key=lambda row: (row["occurred_at"], row["transaction_id"])),
            "currency_totals": [{"currency": currency, **{key: str(value) for key, value in amounts.items()}}
                                for currency, amounts in sorted(totals.items())],
            "transaction_scope": "selected graph window only; rule evidence outside this window is not included",
            "profile_status": "Unavailable: verified customer, balance, account-opening and device data are not supplied."}
