from oscar.core.loading import get_model


def create_default_accounts():
    """Create the default structure (idempotent / safe to re-run)"""
    from oscar_accounts import names

    AccountType = get_model("oscar_accounts", "AccountType")

    def get_or_add_root(name: str):
        node = AccountType.get_root_nodes().filter(name=name).first()
        return node or AccountType.add_root(name=name)

    def get_or_add_child(parent, name: str):
        node = parent.get_children().filter(name=name).first()
        return node or parent.add_child(name=name)

    def get_or_create_account(account_type_node, name: str, **defaults):
        # Related manager soporta get_or_create
        obj, created = account_type_node.accounts.get_or_create(
            name=name,
            defaults=defaults or None,
        )
        # Opcional: si ya existía, “sincroniza” defaults (ej: credit_limit=None)
        if (not created) and defaults:
            changed = False
            for k, v in defaults.items():
                if getattr(obj, k) != v:
                    setattr(obj, k, v)
                    changed = True
            if changed:
                obj.save(update_fields=list(defaults.keys()))
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
