from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth / Users (FR-1, FR-3) ----------
class RegisterRequest(BaseModel):
    owner_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    business_name: str = Field(min_length=1, max_length=255)
    business_address: str | None = None
    business_phone: str | None = None


class LoginRequest(BaseModel):
    username: str  # email or phone
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None
    is_active: bool

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(Owner|Manager|Cashier)$")


class EmployeeOut(BaseModel):
    membership_id: int
    user: UserOut
    role: str
    is_active: bool


class EmployeeRoleUpdate(BaseModel):
    role: str = Field(pattern="^(Owner|Manager|Cashier)$")


# ---------- Business (FR-2) ----------
class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    currency: str | None = "BDT"
    tax_rate: float | None = 0.0


class BusinessOut(BaseModel):
    id: int
    name: str
    address: str | None
    phone: str | None
    email: str | None
    logo_path: str | None
    currency: str
    tax_rate: float
    invoice_format: str
    min_stock_default: int

    class Config:
        from_attributes = True


class BusinessUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    currency: str | None = None
    tax_rate: float | None = None
    invoice_format: str | None = None
    min_stock_default: int | None = None


# ---------- Category (FR-4) ----------
class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Product (FR-5) ----------
class ProductCreate(BaseModel):
    name: str
    sku: str
    barcode: str | None = None
    category_id: int | None = None
    brand: str | None = None
    unit: str = "pcs"
    purchase_price: float = 0
    selling_price: float = 0
    min_stock: int = 5


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: int | None = None
    brand: str | None = None
    unit: str | None = None
    purchase_price: float | None = None
    selling_price: float | None = None
    min_stock: int | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    barcode: str | None
    category_id: int | None
    brand: str | None
    unit: str
    purchase_price: float
    selling_price: float
    min_stock: int
    quantity_on_hand: int
    is_active: bool
    image_path: str | None

    class Config:
        from_attributes = True


# ---------- Supplier / Customer (FR-6, FR-7) ----------
class SupplierCreate(BaseModel):
    company_name: str
    contact_person: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None


class SupplierOut(SupplierCreate):
    id: int
    outstanding_balance: float
    is_active: bool

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    credit_limit: float = 0


class CustomerOut(CustomerCreate):
    id: int
    outstanding_balance: float
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Inventory (FR-8, FR-9) ----------
class AdjustRequest(BaseModel):
    product_id: int
    quantity_change: int
    reason: str = Field(min_length=1)


class InventoryTxOut(BaseModel):
    id: int
    product_id: int
    quantity_change: int
    tx_type: str
    reason: str | None
    user_id: int | None
    related_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PriceAdjustRequest(BaseModel):
    """Optional-field price adjustment: provide sell price, cost price or both."""

    product_id: int
    new_selling_price: float | None = Field(default=None, ge=0)
    new_purchase_price: float | None = Field(default=None, ge=0)
    reason: str = Field(min_length=1)


class PriceAdjustmentOut(BaseModel):
    id: int
    product_id: int
    old_selling_price: float
    new_selling_price: float
    old_purchase_price: float
    new_purchase_price: float
    reason: str
    user_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Purchases (FR-10) ----------
class PurchaseItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0)


class PurchaseCreate(BaseModel):
    supplier_id: int
    items: list[PurchaseItemIn] = Field(min_length=1)
    discount_amount: float = 0
    tax_amount: float = 0
    paid_amount: float = 0
    note: str | None = None


class PurchaseItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_cost: float
    line_total: float

    class Config:
        from_attributes = True


class PurchaseOut(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str | None = None
    purchase_date: datetime
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    paid_amount: float
    payment_status: str
    status: str
    note: str | None = None
    items: list[PurchaseItemOut] = []

    class Config:
        from_attributes = True


class PurchasePayRequest(BaseModel):
    amount: float = Field(gt=0)


# ---------- Sales / POS (FR-11, FR-12, FR-13) ----------
class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: float | None = None  # default: product.selling_price
    discount: float = 0


class CheckoutRequest(BaseModel):
    items: list[CartItemIn] = Field(min_length=1)
    customer_id: int | None = None
    discount_amount: float = 0
    tax_percent: float = 0
    paid_amount: float | None = None  # default: full total
    payment_method: str = "cash"


class SaleItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: float
    discount: float
    line_total: float
    returned_qty: int

    class Config:
        from_attributes = True


class SaleOut(BaseModel):
    id: int
    invoice_no: str
    customer_id: int | None = None
    customer_name: str | None = None
    subtotal: float
    discount_amount: float
    tax_percent: float
    tax_amount: float
    total_amount: float
    paid_amount: float
    payment_method: str
    payment_status: str
    status: str
    created_at: datetime
    items: list[SaleItemOut] = []

    class Config:
        from_attributes = True


# ---------- Returns (FR-14) ----------
class ReturnItemIn(BaseModel):
    sale_item_id: int
    quantity: int = Field(gt=0)


class ReturnCreate(BaseModel):
    sale_id: int
    reason: str = Field(min_length=1)
    items: list[ReturnItemIn] = Field(min_length=1)


class ReturnOut(BaseModel):
    id: int
    sale_id: int
    reason: str
    refund_amount: float
    created_at: datetime


class EmployeeResetRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class SaleCancelRequest(BaseModel):
    reason: str = Field(min_length=1)


# ---------- Phase 4: business settings / subscriptions (FR-28, FR-29) ----------
class SettingsOut(BaseModel):
    currency: str
    tax_rate: float
    invoice_format: str
    min_stock_default: int
    business_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class SettingsUpdate(BaseModel):
    currency: str | None = None
    tax_rate: float | None = None
    invoice_format: str | None = None
    min_stock_default: int | None = None
    business_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    product_limit: int
    employee_limit: int
    product_count: int
    employee_count: int
    product_usage_pct: float
    employee_usage_pct: float
    near_limit: bool
    at_limit: bool
    message: str | None = None

    class Config:
        from_attributes = True


class SubscriptionUpdate(BaseModel):
    plan: str = Field(pattern="^(free|basic|pro)$")


# ---------- Phase 5: AI (FR-30..FR-37) ----------
class AIChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    save: bool = True


class AIChatResponse(BaseModel):
    answer: str
    data: dict
    recommendation_id: int | None = None


class AISummaryRequest(BaseModel):
    kind: str = Field(pattern="^(sales|expenses|inventory|profit)$")
    preset: str = "month"


class AIRecommendationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    reviewed: bool
    acted_upon: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AIRecommendationUpdate(BaseModel):
    reviewed: bool | None = None
    acted_upon: bool | None = None


# ---------- Expenses (FR-15) ----------
class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    description: str | None = None
    expense_date: datetime | None = None
    payment_method: str = "cash"


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=50)
    amount: float | None = Field(default=None, gt=0)
    description: str | None = None
    expense_date: datetime | None = None
    payment_method: str | None = None


class ExpenseOut(BaseModel):
    id: int
    category: str
    amount: float
    description: str | None = None
    expense_date: datetime
    payment_method: str
    created_at: datetime

    class Config:
        from_attributes = True
