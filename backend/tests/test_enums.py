"""Tests for the string enums used across the domain model."""

import pytest

from app.models.enums import InventoryTxType, Role


def test_role_values_are_serializable_strings() -> None:
    assert Role.OWNER == "Owner"
    assert Role.MANAGER == "Manager"
    assert Role.CASHIER == "Cashier"


def test_role_can_be_iterated() -> None:
    members = list(Role)
    assert len(members) == 3
    assert Role("Manager") is Role.MANAGER


def test_inventory_tx_type_values() -> None:
    assert InventoryTxType.PURCHASE == "purchase"
    assert InventoryTxType.SALE == "sale"
    assert InventoryTxType.RETURN == "return"
    assert InventoryTxType.ADJUSTMENT == "adjustment"


def test_inventory_tx_type_is_bidirectional() -> None:
    assert InventoryTxType("sale") is InventoryTxType.SALE
    with pytest.raises(ValueError):
        InventoryTxType("not-a-real-type")  # type: ignore[arg-type]
