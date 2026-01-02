from django.db import IntegrityError
from oscar.core.loading import get_model


def create_default_accounts():
    """Create the default structure (idempotent / safe to re-run)"""
    from oscar_accounts import names

    AccountType = get_model("oscar_accounts", "AccountType")
    Account = get_model("oscar_accounts", "Account")

    def get_or_add_root(name: str):
        node = AccountType.get_root_nodes().filter(name=name).first()
        return node or AccountType.add_root(name=name)

    def get_or_add_child(parent, name: str):
        node = parent.get_children().filter(name=name).first()
        return node or parent.add_child(name=name)

    def get_or_create_account(account_type_node, name: str, credit_limit=None):
        """
        Account.name es UNIQUE global, así que NO podemos usar:
            account_type_node.accounts.get_or_create(name=...)
        porque si existe con otro account_type, falla con IntegrityError.

        Esta función crea o reutiliza por name, y asegura account_type correcto.
        """
        try:
            obj, created = Account.objects.get_or_create(
                name=name,
                defaults={
                    "account_type": account_type_node,
                    "credit_limit": credit_limit,
                },
            )
        except IntegrityError:
            # ya existe por el UNIQUE(name) pero en otro account_type
            obj = Account.objects.get(name=name)
            created = False

        if obj.account_type_id != account_type_node.pk:
            obj.account_type = account_type_node
            obj.save(update_fields=["account_type"])

        # si quieres también “arreglar” credit_limit cuando sea None:
        if credit_limit is None and obj.credit_limit is not None:
            obj.credit_limit = None
            obj.save(update_fields=["credit_limit"])

        return obj

    # ---------- Assets tree ----------
    assets = get_or_add_root(names.ASSETS)

    sales = get_or_add_child(assets, names.SALES)
    get_or_create_account(sales, names.REDEMPTIONS)
    get_or_create_account(sales, names.LAPSED)

    cash = get_or_add_child(assets, names.CASH)
    get_or_create_account(cash, names.BANK, credit_limit=None)

    unpaid = get_or_add_child(assets, names.UNPAID_ACCOUNT_TYPE)
    for nm in names.UNPAID_ACCOUNTS:
        get_or_create_account(unpaid, nm, credit_limit=None)

    # ---------- Liabilities tree ----------
    liabilities = get_or_add_root(names.LIABILITIES)
    income = get_or_add_child(liabilities, names.DEFERRED_INCOME)
    for nm in names.DEFERRED_INCOME_ACCOUNT_TYPES:
        get_or_add_child(income, nm)
