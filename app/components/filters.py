"""Human-readable labels preserve both bank and account identity."""

def account_label(account):
    return f"{account['bank_id']} : {account['account_id']}"


def humanize(value):
    return value.replace("_", " ").capitalize()
