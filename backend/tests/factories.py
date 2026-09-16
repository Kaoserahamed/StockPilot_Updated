"""API-driven test data builders.

Everything is created through the public HTTP API rather than by writing rows
directly, so fixtures exercise the same validation, role checks, tenancy guards
and audit writes that real clients hit.

Helpers assert on the setup call's status code, so a broken prerequisite is
reported at the point it breaks instead of surfacing later as a confusing
failure inside the test body.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

API = "/api/v1"
DEFAULT_PASSWORD = "secret123"


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
def register_owner(
    client: TestClient,
    email: str = "owner@test.com",
    business_name: str = "Test Shop",
    password: str = DEFAULT_PASSWORD,
    owner_name: str = "Owner",
) -> dict:
    """Register an owner plus their first business, and return auth headers."""
    resp = client.post(
        f"{API}/auth/register",
        json={
            "owner_name": owner_name,
            "email": email,
            "password": password,
            "business_name": business_name,
        },
    )
    assert resp.status_code == 201, resp.text
    return login(client, email, password)


def login(client: TestClient, username: str, password: str = DEFAULT_PASSWORD) -> dict:
    """Authenticate and return a ready-to-use Authorization header dict."""
    resp = client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_employee(
    client: TestClient,
    headers: dict,
    name: str = "Cashier One",
    email: str = "cashier@test.com",
    role: str = "Cashier",
    password: str = DEFAULT_PASSWORD,
) -> dict:
    resp = client.post(
        f"{API}/employees",
        json={"name": name, "email": email, "password": password, "role": role},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_cashier(client: TestClient, headers: dict, email: str = "cashier@test.com") -> dict:
    """Create a Cashier employee and return that employee's own auth headers."""
    create_employee(client, headers, name="Cashier One", email=email, role="Cashier")
    return login(client, email)


# --------------------------------------------------------------------------- #
# Catalogue and parties
# --------------------------------------------------------------------------- #
def create_category(client: TestClient, headers: dict, name: str = "Grocery", **extra) -> dict:
    resp = client.post(f"{API}/categories", json={"name": name, **extra}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_product(
    client: TestClient,
    headers: dict,
    name: str = "Rice 1kg",
    sku: str = "RICE-001",
    selling_price: float = 100,
    purchase_price: float = 60,
    min_stock: int = 5,
    **extra,
) -> dict:
    payload = {
        "name": name,
        "sku": sku,
        "selling_price": selling_price,
        "purchase_price": purchase_price,
        "min_stock": min_stock,
        **extra,
    }
    resp = client.post(f"{API}/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_supplier(
    client: TestClient, headers: dict, company_name: str = "Acme Supplies", **extra
) -> dict:
    resp = client.post(f"{API}/suppliers", json={"company_name": company_name, **extra}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_customer(client: TestClient, headers: dict, name: str = "Walk-in", **extra) -> dict:
    resp = client.post(f"{API}/customers", json={"name": name, **extra}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Stock, sales and money
# --------------------------------------------------------------------------- #
def adjust_stock(
    client: TestClient,
    headers: dict,
    product_id: int,
    quantity_change: int,
    reason: str = "opening stock",
) -> dict:
    resp = client.post(
        f"{API}/inventory/adjust",
        json={"product_id": product_id, "quantity_change": quantity_change, "reason": reason},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_purchase(
    client: TestClient,
    headers: dict,
    supplier_id: int,
    items: list[dict],
    paid_amount: float = 0,
    **extra,
) -> dict:
    """Receive stock through a real purchase so movements stay realistic."""
    resp = client.post(
        f"{API}/purchases",
        json={"supplier_id": supplier_id, "items": items, "paid_amount": paid_amount, **extra},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def stock_up(
    client: TestClient,
    headers: dict,
    supplier_id: int,
    product_id: int,
    quantity: int = 10,
    unit_cost: float = 60,
) -> dict:
    """Convenience wrapper: single-line purchase that puts stock on the shelf."""
    return create_purchase(
        client,
        headers,
        supplier_id,
        [{"product_id": product_id, "quantity": quantity, "unit_cost": unit_cost}],
    )


def checkout(client: TestClient, headers: dict, items: list[dict], **extra) -> dict:
    resp = client.post(f"{API}/sales/checkout", json={"items": items, **extra}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_return(
    client: TestClient,
    headers: dict,
    sale_id: int,
    items: list[dict],
    reason: str = "damaged",
) -> dict:
    resp = client.post(
        f"{API}/returns",
        json={"sale_id": sale_id, "reason": reason, "items": items},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_expense(
    client: TestClient, headers: dict, category: str = "rent", amount: float = 50, **extra
) -> dict:
    resp = client.post(
        f"{API}/expenses", json={"category": category, "amount": amount, **extra}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def product_quantity(client: TestClient, headers: dict, product_id: int) -> int:
    resp = client.get(f"{API}/products/{product_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["quantity_on_hand"]


# --------------------------------------------------------------------------- #
# Composite fixture
# --------------------------------------------------------------------------- #
@dataclass
class Shop:
    """A shop whose prerequisites are already in place, with stock on hand."""

    headers: dict
    business: dict
    supplier: dict
    product: dict
    customer: dict
    stock_quantity: int = 10

    @property
    def product_id(self) -> int:
        return self.product["id"]

    @property
    def supplier_id(self) -> int:
        return self.supplier["id"]

    @property
    def customer_id(self) -> int:
        return self.customer["id"]

    def qty(self, client: TestClient) -> int:
        """Current on-hand quantity for the seeded product."""
        return product_quantity(client, self.headers, self.product_id)


def seed_shop(
    client: TestClient,
    email: str = "owner@test.com",
    business_name: str = "Test Shop",
    quantity: int = 10,
    unit_cost: float = 60,
    selling_price: float = 100,
    min_stock: int = 5,
) -> Shop:
    """Build a complete shop: owner, supplier, product, customer and stock."""
    headers = register_owner(client, email=email, business_name=business_name)
    business = client.get(f"{API}/businesses/me", headers=headers).json()
    supplier = create_supplier(client, headers)
    product = create_product(
        client,
        headers,
        selling_price=selling_price,
        purchase_price=unit_cost,
        min_stock=min_stock,
    )
    customer = create_customer(client, headers, name="Walk-in")

    if quantity:
        stock_up(
            client,
            headers,
            supplier_id=supplier["id"],
            product_id=product["id"],
            quantity=quantity,
            unit_cost=unit_cost,
        )
        product = client.get(f"{API}/products/{product['id']}", headers=headers).json()

    return Shop(
        headers=headers,
        business=business,
        supplier=supplier,
        product=product,
        customer=customer,
        stock_quantity=quantity,
    )

