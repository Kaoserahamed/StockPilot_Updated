"""Product catalogue (FR-5): CRUD, uniqueness, search, filters and soft delete."""

from fastapi.testclient import TestClient

from tests import factories

PRODUCTS = "/api/v1/products"


def test_create_product_with_full_attribute_set(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod1@test.com")
    category = factories.create_category(client, headers)

    resp = client.post(
        PRODUCTS,
        json={
            "name": "Rice 1kg",
            "sku": "RICE-001",
            "barcode": "8901234567890",
            "category_id": category["id"],
            "brand": "ACI",
            "unit": "kg",
            "purchase_price": 60,
            "selling_price": 75,
            "min_stock": 10,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Rice 1kg"
    assert body["sku"] == "RICE-001"
    assert body["barcode"] == "8901234567890"
    assert body["brand"] == "ACI"
    assert body["unit"] == "kg"
    assert body["purchase_price"] == 60
    assert body["selling_price"] == 75
    assert body["min_stock"] == 10
    assert body["quantity_on_hand"] == 0
    assert body["is_active"] is True


def test_create_product_defaults_are_sane(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod2@test.com")
    body = factories.create_product(client, headers, name="Soap", sku="SOAP-1")
    assert body["unit"] == "pcs"
    assert body["quantity_on_hand"] == 0
    assert body["is_active"] is True


def test_duplicate_sku_within_a_business_is_rejected(client: TestClient) -> None:
    """FR-5.7."""
    headers = factories.register_owner(client, email="prod3@test.com")
    factories.create_product(client, headers, sku="DUP-1")

    resp = client.post(PRODUCTS, json={"name": "Other", "sku": "DUP-1"}, headers=headers)
    assert resp.status_code == 409, resp.text
    assert "Duplicate" in resp.json()["detail"]


def test_duplicate_barcode_within_a_business_is_rejected(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod4@test.com")
    factories.create_product(client, headers, sku="A-1", barcode="123456")

    resp = client.post(
        PRODUCTS, json={"name": "Other", "sku": "B-1", "barcode": "123456"}, headers=headers
    )
    assert resp.status_code == 409


def test_products_without_a_barcode_do_not_collide(client: TestClient) -> None:
    """FR-5.7: an empty barcode is stored as NULL, so many products may omit it."""
    headers = factories.register_owner(client, email="prod5@test.com")
    factories.create_product(client, headers, name="One", sku="NB-1")

    second = client.post(PRODUCTS, json={"name": "Two", "sku": "NB-2"}, headers=headers)
    assert second.status_code == 201, second.text

    empty = client.post(
        PRODUCTS, json={"name": "Three", "sku": "NB-3", "barcode": ""}, headers=headers
    )
    assert empty.status_code == 201, empty.text
    assert empty.json()["barcode"] is None


def test_same_sku_is_allowed_in_a_different_business(client: TestClient) -> None:
    first = factories.register_owner(client, email="prod6@test.com")
    second = factories.register_owner(client, email="prod7@test.com")

    factories.create_product(client, first, sku="SHARED-1")
    other = client.post(PRODUCTS, json={"name": "Mine", "sku": "SHARED-1"}, headers=second)
    assert other.status_code == 201


def test_product_with_unknown_category_is_rejected(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod8@test.com")
    resp = client.post(
        PRODUCTS, json={"name": "X", "sku": "X-1", "category_id": 99999}, headers=headers
    )
    assert resp.status_code == 400


def test_product_cannot_reference_another_business_category(client: TestClient) -> None:
    first = factories.register_owner(client, email="prod9@test.com")
    second = factories.register_owner(client, email="prod10@test.com")
    foreign = factories.create_category(client, first, name="Foreign")

    resp = client.post(
        PRODUCTS,
        json={"name": "X", "sku": "X-9", "category_id": foreign["id"]},
        headers=second,
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Search and filtering (FR-5.6)
# --------------------------------------------------------------------------- #
def test_search_matches_name_sku_barcode_and_brand(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod11@test.com")
    factories.create_product(
        client, headers, name="Rice 1kg", sku="RICE-001", barcode="111", brand="ACI"
    )
    factories.create_product(
        client, headers, name="Oil 1L", sku="OIL-001", barcode="222", brand="Fresh"
    )

    for query in ("RICE", "111", "ACI"):
        resp = client.get(f"{PRODUCTS}?q={query}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1, f"query {query!r} returned {resp.json()}"


def test_filter_products_by_category(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod12@test.com")
    grocery = factories.create_category(client, headers, name="Grocery")
    other = factories.create_category(client, headers, name="Other")
    factories.create_product(client, headers, name="Rice", sku="R-1", category_id=grocery["id"])
    factories.create_product(client, headers, name="Soap", sku="S-1", category_id=other["id"])

    resp = client.get(f"{PRODUCTS}?category_id={grocery['id']}", headers=headers)
    assert [p["name"] for p in resp.json()] == ["Rice"]


def test_low_stock_and_out_of_stock_filters(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod13@test.com")
    stocked = factories.create_product(client, headers, name="Plenty", sku="P-1", min_stock=5)
    low = factories.create_product(client, headers, name="Low", sku="L-1", min_stock=5)

    factories.adjust_stock(client, headers, stocked["id"], 50)
    factories.adjust_stock(client, headers, low["id"], 2)

    low_ids = [p["id"] for p in client.get(f"{PRODUCTS}?low_stock=true", headers=headers).json()]
    assert low_ids == [low["id"]]

    empty_ids = [
        p["id"] for p in client.get(f"{PRODUCTS}?out_of_stock=true", headers=headers).json()
    ]
    assert stocked["id"] not in empty_ids


def test_pagination_window_is_respected(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod14@test.com")
    for index in range(5):
        factories.create_product(client, headers, name=f"Item {index}", sku=f"P-{index}")

    assert len(client.get(f"{PRODUCTS}?limit=2&offset=0", headers=headers).json()) == 2
    assert len(client.get(f"{PRODUCTS}?limit=2&offset=4", headers=headers).json()) == 1
    assert client.get(f"{PRODUCTS}?limit=0", headers=headers).status_code == 422


# --------------------------------------------------------------------------- #
# Read, update and soft delete
# --------------------------------------------------------------------------- #
def test_get_single_product_and_unknown_id(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod15@test.com")
    product = factories.create_product(client, headers)

    assert client.get(f"{PRODUCTS}/{product['id']}", headers=headers).status_code == 200
    assert client.get(f"{PRODUCTS}/999999", headers=headers).status_code == 404


def test_update_product_fields(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod16@test.com")
    product = factories.create_product(client, headers, name="Rice", sku="U-1")

    resp = client.patch(
        f"{PRODUCTS}/{product['id']}",
        json={"name": "Basmati Rice", "selling_price": 150, "min_stock": 20},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Basmati Rice"
    assert body["selling_price"] == 150
    assert body["min_stock"] == 20


def test_price_change_writes_an_audit_entry(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod17@test.com")
    product = factories.create_product(client, headers, sku="AUD-1", selling_price=100)

    client.patch(f"{PRODUCTS}/{product['id']}", json={"selling_price": 120}, headers=headers)

    logs = client.get("/api/v1/audit-logs", headers=headers).json()
    entry = next(log for log in logs if log["action"] == "product.price_change")
    assert float(entry["old_value"]) == 100
    assert float(entry["new_value"]) == 120


def test_unchanged_price_does_not_write_an_audit_entry(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod18@test.com")
    product = factories.create_product(client, headers, sku="AUD-2", selling_price=100)

    client.patch(f"{PRODUCTS}/{product['id']}", json={"name": "Renamed"}, headers=headers)

    actions = [log["action"] for log in client.get("/api/v1/audit-logs", headers=headers).json()]
    assert "product.price_change" not in actions


def test_deactivate_hides_from_pos_then_activate_restores(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod19@test.com")
    product = factories.create_product(client, headers, name="Rice", sku="ACT-1")

    off = client.post(f"{PRODUCTS}/{product['id']}/deactivate", headers=headers)
    assert off.status_code == 200
    assert off.json()["is_active"] is False
    hidden = client.get("/api/v1/pos/search?q=Rice", headers=headers).json()
    assert all(row["id"] != product["id"] for row in hidden)

    on = client.post(f"{PRODUCTS}/{product['id']}/activate", headers=headers)
    assert on.status_code == 200
    assert on.json()["is_active"] is True
    visible = client.get("/api/v1/pos/search?q=Rice", headers=headers).json()
    assert any(row["id"] == product["id"] for row in visible)


def test_activate_is_idempotent(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod20@test.com")
    product = factories.create_product(client, headers, sku="ACT-2")

    resp = client.post(f"{PRODUCTS}/{product['id']}/activate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_product_writes_are_recorded_in_the_audit_log(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod21@test.com")
    product = factories.create_product(client, headers, sku="ACT-3")

    client.post(f"{PRODUCTS}/{product['id']}/deactivate", headers=headers)
    client.post(f"{PRODUCTS}/{product['id']}/activate", headers=headers)

    actions = [log["action"] for log in client.get("/api/v1/audit-logs", headers=headers).json()]
    assert "product.deactivate" in actions
    assert "product.activate" in actions


# --------------------------------------------------------------------------- #
# Authorisation
# --------------------------------------------------------------------------- #
def test_cashier_cannot_write_to_the_catalogue(client: TestClient) -> None:
    headers = factories.register_owner(client, email="prod22@test.com")
    product = factories.create_product(client, headers, sku="RBAC-1")
    cashier = factories.create_cashier(client, headers, email="prod-cashier@test.com")

    assert (
        client.post(PRODUCTS, json={"name": "X", "sku": "NOPE"}, headers=cashier).status_code == 403
    )
    assert (
        client.patch(f"{PRODUCTS}/{product['id']}", json={"name": "X"}, headers=cashier).status_code
        == 403
    )
    assert client.post(f"{PRODUCTS}/{product['id']}/deactivate", headers=cashier).status_code == 403
    assert client.post(f"{PRODUCTS}/{product['id']}/activate", headers=cashier).status_code == 403

    # reads remain available to a cashier (needed for POS)
    assert client.get(PRODUCTS, headers=cashier).status_code == 200


def test_catalogue_requires_authentication(client: TestClient) -> None:
    assert client.get(PRODUCTS).status_code == 401
    assert client.post(PRODUCTS, json={"name": "Anon", "sku": "ANON"}).status_code == 401
