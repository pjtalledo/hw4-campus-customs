from pydantic import BaseModel
from typing import List, Optional


class ProductContext(BaseModel):
    """Current product being viewed, sent from ProductDetail so the agent
    can resolve references like 'this' or 'it'."""
    product_id: str
    name: str
    price: float
    description: Optional[str] = None
    garment_type: Optional[str] = None
    colors: List[str] = []


class PageContext(BaseModel):
    """Current page the shopper is on."""
    page_type: str  # "general" | "products_list" | "product_detail"
    product: Optional[ProductContext] = None


class ChatRequest(BaseModel):
    """Chat message request from frontend."""
    message: str
    user_id: Optional[int] = None
    page_context: Optional[PageContext] = None


class SearchProduct(BaseModel):
    """Product information for search results."""
    product_id: str
    name: str
    price: float
    short_description: str
    image_file_path: str


class ChatResponse(BaseModel):
    """Chat response with agent reply and optional product matches."""
    reply: str
    products: List[SearchProduct] = []


class ChatHistoryMessage(BaseModel):
    """A single stored chat message for history reconstruction."""
    role: str
    content: str
    products: List[SearchProduct] = []
    created_at: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Chronological chat history for a logged-in user."""
    messages: List[ChatHistoryMessage] = []


# Problem 6: Tool return models

class ProductInfo(BaseModel):
    """Product information from database."""
    found: bool
    product_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    garment_type: Optional[str] = None


class SizeStock(BaseModel):
    """Stock for a specific size."""
    size: str
    quantity: int
    in_stock: bool  # True if quantity > 0


class StockInfo(BaseModel):
    """Inventory information for a product."""
    found: bool
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    all_sizes: Optional[List[SizeStock]] = None  # All sizes if no specific size requested
    requested_size: Optional[str] = None  # Only if a specific size was requested
    quantity: Optional[int] = None  # Quantity for requested size


# Problem 9: Variant availability tool return shape (documents the structure
# returned by check_variant_availability's json.dumps payload; the tool
# itself returns a raw JSON string like the other tools for PydanticAI
# compatibility, consistent with ProductInfo/StockInfo above).

class VariantAvailability(BaseModel):
    """Structured description of a product's color/size availability.

    Reflects the real schema limitation: colors are tracked per product
    (catalogue.colors) while quantity is tracked per size (inventory.quantity) -
    there is no color+size combination stock in this database.
    """
    found: bool
    product_id: Optional[str] = None
    name: Optional[str] = None
    listed_colors: List[str] = []
    requested_color: Optional[str] = None
    color_listed: Optional[bool] = None
    requested_size: Optional[str] = None
    quantity: Optional[int] = None
    in_stock: Optional[bool] = None
    schema_note: Optional[str] = None
