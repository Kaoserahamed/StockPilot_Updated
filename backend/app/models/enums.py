import enum


class Role(enum.StrEnum):
    OWNER = "Owner"
    MANAGER = "Manager"
    CASHIER = "Cashier"


class InventoryTxType(enum.StrEnum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
