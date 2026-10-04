import sqlite3
import json
import os
import hashlib
import hmac
import bcrypt
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel

try:
    from .models import ChatRequest, ChatResponse, SearchProduct, ChatHistoryMessage, ChatHistoryResponse
    from .agent import chat as agent_chat
except ImportError:
    from models import ChatRequest, ChatResponse, SearchProduct, ChatHistoryMessage, ChatHistoryResponse
    from agent import chat as agent_chat

app = FastAPI()

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path - relative to this file
DB_PATH = Path(__file__).parent.parent / "data" / "campus_customs.db"
IMAGES_PATH = Path(__file__).parent.parent / "data" / "products"

# Pydantic models
class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    first_name: str
    last_name: str

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt (new accounts) or PBKDF2-HMAC-SHA256 (seeded accounts)."""
    try:
        # Try bcrypt first (for new accounts)
        if password_hash.startswith('$2'):
            return bcrypt.checkpw(password.encode(), password_hash.encode())

        # Try pbkdf2_sha256 (for assignment seeded accounts)
        if password_hash.startswith('pbkdf2_sha256$'):
            parts = password_hash.split('$')
            if len(parts) != 3:
                return False

            algorithm, salt, stored_hash = parts

            # Assignment uses PBKDF2-HMAC-SHA256 with:
            # - iterations: 120000
            # - dklen: 32 bytes
            # - digest: lowercase hexadecimal
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                120000,
                dklen=32
            )
            computed_hash = hash_obj.hex()

            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(computed_hash, stored_hash)

        return False
    except Exception:
        return False

def get_db_connection():
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/products")
def get_products(limit: Optional[int] = None, offset: Optional[int] = 0):
    """Get all products from catalogue, including a computed in_stock flag.

    in_stock = SUM(inventory.quantity) > 0 across all sizes for that product
    (Problem 9 availability filter support). Inventory itself is not modified
    or exposed per-size here to keep the payload minimal.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT c.product_id, c.name, c.price, c.description, c.image_file_path, c.garment_type,
                   COALESCE(SUM(i.quantity), 0) > 0 AS in_stock
            FROM catalogue c
            LEFT JOIN inventory i ON c.product_id = i.product_id
            GROUP BY c.product_id
            ORDER BY c.name
        """

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(query)
        rows = cursor.fetchall()

        products = []
        for row in rows:
            product = dict(row)
            product['in_stock'] = bool(product['in_stock'])
            # Truncate description to first 100 chars for list view
            product['short_description'] = product['description'][:100] + "..." if len(product['description']) > 100 else product['description']
            products.append(product)

        return {"products": products, "count": len(products)}
    finally:
        conn.close()


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    """Get a single product by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        product = dict(row)
        # Parse JSON fields
        product['colors'] = json.loads(product['colors'])
        product['search_tags'] = json.loads(product['search_tags'])

        return product
    finally:
        conn.close()


@app.get("/api/inventory/{product_id}")
def get_inventory(product_id: str):
    """Get inventory/sizes for a product."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # First verify the product exists
        cursor.execute("SELECT product_id FROM catalogue WHERE product_id = ?", (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")

        # Get inventory for this product
        cursor.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY size",
            (product_id,)
        )
        rows = cursor.fetchall()

        inventory = [dict(row) for row in rows]

        return {"product_id": product_id, "inventory": inventory}
    finally:
        conn.close()


@app.post("/api/auth/register")
def register(request: RegisterRequest):
    """Register a new user account."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Validate input
        if not request.first_name or not request.first_name.strip():
            raise HTTPException(status_code=400, detail="First name is required")
        if not request.last_name or not request.last_name.strip():
            raise HTTPException(status_code=400, detail="Last name is required")
        if not request.email or not request.email.strip():
            raise HTTPException(status_code=400, detail="Email is required")
        if not request.password:
            raise HTTPException(status_code=400, detail="Password is required")

        # Normalize email
        email = request.email.strip().lower()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        password_hash = hash_password(request.password)

        # Create full name
        full_name = f"{request.first_name.strip()} {request.last_name.strip()}"

        # Insert user
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, password_hash, request.first_name.strip(), request.last_name.strip())
        )
        conn.commit()

        # Get the created user
        cursor.execute("SELECT id, name, email, first_name, last_name FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        user = dict(row)

        return {"success": True, "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration failed")
    finally:
        conn.close()


@app.post("/api/auth/login")
def login(request: LoginRequest):
    """Log in a user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Validate input
        if not request.email or not request.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Normalize email
        email = request.email.strip().lower()

        # Find user by email
        cursor.execute("SELECT id, name, email, password_hash, first_name, last_name FROM users WHERE LOWER(email) = ?", (email,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_data = dict(row)
        stored_hash = user_data['password_hash']

        # Verify password
        if not verify_password(request.password, stored_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Return user info (without password_hash)
        return {
            "success": True,
            "user": {
                "id": user_data['id'],
                "name": user_data['name'],
                "email": user_data['email'],
                "first_name": user_data['first_name'],
                "last_name": user_data['last_name']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed")
    finally:
        conn.close()


@app.get("/images/{filename}")
def get_image(filename: str):
    """Serve product images safely."""
    # Security: only allow filenames that look like product images
    if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = IMAGES_PATH / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path)


def _get_user_identity(user_id: int):
    """Look up a user's name/email for agent identity. Returns None if not found."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, email FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _get_recent_history(user_id: int, limit: int = 20):
    """Fetch the user's most recent chat messages in chronological order."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT role, content FROM chat_messages
               WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()


def _save_chat_message(user_id: int, role: str, content: str, products_json: Optional[str] = None):
    """Persist one chat message row. Only called for logged-in users."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, products_json)
        )
        conn.commit()
    finally:
        conn.close()


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Handle chatbot messages via PydanticAI agent.

    For logged-in shoppers (request.user_id set), persists both the user's
    message and the assistant's reply to chat_messages, and supplies recent
    conversation history plus shopper identity/page context to the agent.
    Guest requests (user_id is None) are not persisted.
    """
    try:
        user_name = None
        user_email = None
        history = None

        if request.user_id is not None:
            identity = _get_user_identity(request.user_id)
            if identity:
                user_name = identity["name"]
                user_email = identity["email"]
                history = _get_recent_history(request.user_id)

        page_context_dict = request.page_context.model_dump() if request.page_context else None

        reply_text, products_data = await agent_chat(
            request.message,
            user_id=request.user_id,
            user_name=user_name,
            user_email=user_email,
            page_context=page_context_dict,
            history=history,
        )

        # Convert product data to SearchProduct models
        products = []
        if products_data:
            for prod in products_data:
                products.append(SearchProduct(
                    product_id=prod.get("product_id", ""),
                    name=prod.get("name", ""),
                    price=float(prod.get("price", 0)),
                    short_description=prod.get("short_description", ""),
                    image_file_path=prod.get("image_file_path", "")
                ))

        # Persist both turns for logged-in shoppers only
        if request.user_id is not None and user_name is not None:
            _save_chat_message(request.user_id, "user", request.message, None)
            products_json = json.dumps([p.model_dump() for p in products]) if products else None
            _save_chat_message(request.user_id, "assistant", reply_text, products_json)

        return ChatResponse(reply=reply_text, products=products)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        # Log the actual error server-side for debugging
        logger.exception(f"Chat error for message: {request.message}")
        # Return generic customer-friendly message without exposing internal details
        return ChatResponse(reply="I apologize, but I'm having trouble responding right now. Please try again.", products=[])


@app.get("/api/chat/history/{user_id}")
def get_chat_history(user_id: int):
    """Return a logged-in shopper's chat history in chronological order.

    Coursework limitation: this project has no server-side session/token
    system (Problem 4 uses localStorage-only client identity), so user_id is
    trusted as sent by the frontend, consistent with the rest of the app's
    auth model. A production system would authenticate this via a session
    token rather than a client-supplied id.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT role, content, products_json, created_at FROM chat_messages
               WHERE user_id = ? ORDER BY id ASC""",
            (user_id,)
        )
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            products = []
            if row["products_json"]:
                try:
                    products = [SearchProduct(**p) for p in json.loads(row["products_json"])]
                except (json.JSONDecodeError, TypeError, ValueError):
                    products = []
            messages.append(ChatHistoryMessage(
                role=row["role"],
                content=row["content"],
                products=products,
                created_at=row["created_at"],
            ))

        return ChatHistoryResponse(messages=messages)
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
