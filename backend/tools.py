"""Agent tools for Campus Customs chatbot.

Problem 6 implements real database lookup tools for product information and stock.
These tools are registered with the PydanticAI Agent to ground responses in database facts.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from pydantic_ai.tools import RunContext


def get_db_path() -> Path:
    """Get the database path relative to this file."""
    return Path(__file__).parent.parent / "data" / "campus_customs.db"


def _find_product_by_name(query: str) -> Optional[dict]:
    """Find a product by name or partial match. Returns dict with product info."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()

        # Try exact match, case-insensitive, then partial
        for where_clause in [
            "name = ?",
            "LOWER(name) = LOWER(?)",
            "LOWER(name) LIKE LOWER(?)",
        ]:
            pattern = query if "LIKE" in where_clause else query
            if "LIKE" in where_clause:
                pattern = f"%{query}%"

            cursor.execute(
                f"SELECT product_id, name, description, price, garment_type FROM catalogue WHERE {where_clause} LIMIT 1",
                (pattern,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    "product_id": result[0],
                    "name": result[1],
                    "description": result[2],
                    "price": result[3],
                    "garment_type": result[4],
                }
        return None
    finally:
        conn.close()


def _normalize_size(size_input: str) -> Optional[str]:
    """Normalize size input to database format."""
    size_map = {
        'S': 'S', 'small': 'S', 'sm': 'S',
        'M': 'M', 'medium': 'M', 'md': 'M',
        'L': 'L', 'large': 'L', 'lg': 'L',
        'XL': 'XL', 'extra large': 'XL', 'xl': 'XL',
        'XS': 'XS', 'extra small': 'XS', 'xs': 'XS',
        'XXL': 'XXL', 'double xl': 'XXL', 'xxl': 'XXL', '2xl': 'XXL',
    }
    normalized = size_map.get(size_input.lower().strip())
    return normalized


def register_tools(agent) -> None:
    """Register PydanticAI tools with the agent.

    Includes Problem 6 product lookup tools and Problem 7 search tool.
    """

    @agent.tool
    def search_products(ctx: RunContext, query: str) -> str:
        """Search the product catalogue by category, type, or keyword.

        Use this when customer asks to browse/show/find products or a category.
        Returns matching catalogue products with basic information.

        Args:
            query: Search query (e.g., "hoodies", "T-shirts", "crewneck", "Yale sports")

        Returns:
            JSON string with matching products
        """
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.cursor()

            query_clean = query.lower().strip()
            # Build singular variant since catalogue garment_type is singular
            # (e.g. "hoodie", "pullover hoodie") but customers often ask in
            # plural ("hoodies", "T-shirts")
            singular = query_clean[:-1] if query_clean.endswith('s') and len(query_clean) > 1 else query_clean
            candidates = [query_clean] if singular == query_clean else [query_clean, singular]

            results = []
            for candidate in candidates:
                cursor.execute(
                    """SELECT product_id, name, price, description, image_file_path
                       FROM catalogue
                       WHERE LOWER(garment_type) LIKE LOWER(?)
                       LIMIT 8""",
                    (f"%{candidate}%",)
                )
                results = cursor.fetchall()
                if results:
                    break

            # If no results, try searching name, description, search_tags
            if not results:
                for candidate in candidates:
                    cursor.execute(
                        """SELECT product_id, name, price, description, image_file_path
                           FROM catalogue
                           WHERE LOWER(name) LIKE LOWER(?)
                              OR LOWER(description) LIKE LOWER(?)
                              OR LOWER(search_tags) LIKE LOWER(?)
                           LIMIT 8""",
                        (f"%{candidate}%", f"%{candidate}%", f"%{candidate}%")
                    )
                    results = cursor.fetchall()
                    if results:
                        break

            if not results:
                return json.dumps({"found": False, "products": [], "message": f"No products found matching '{query}'"})

            products = []
            for row in results:
                # Truncate description to first 60 chars for card display
                desc = row[3]
                short_desc = desc[:60] + "..." if len(desc) > 60 else desc

                products.append({
                    "product_id": row[0],
                    "name": row[1],
                    "price": row[2],
                    "short_description": short_desc,
                    "image_file_path": row[4]
                })

            # Store products on the per-request deps object (RunContext.deps is
            # the same object instance passed into agent.run(), so mutating it
            # here is visible to the caller after the run completes - unlike
            # contextvars, this is not copied per-task/thread).
            if ctx is not None and hasattr(ctx, 'deps') and ctx.deps is not None:
                ctx.deps.products = products

            return json.dumps({
                "found": True,
                "products": products,
                "message": f"Found {len(products)} product(s) matching '{query}'"
            })
        finally:
            conn.close()

    @agent.tool
    def product_info(ctx: RunContext, product_name: str) -> str:
        """Look up exact product information from the database.

        Use this when customer asks about product description or price.
        Returns product details including exact price from database.

        Args:
            product_name: Name or partial name of the product

        Returns:
            JSON string with product info or not found message
        """
        result = _find_product_by_name(product_name)
        if not result:
            return json.dumps({"found": False, "message": f"Product '{product_name}' not found in database"})

        return json.dumps({
            "found": True,
            "product_id": result["product_id"],
            "name": result["name"],
            "description": result["description"],
            "price": result["price"],
            "garment_type": result["garment_type"],
        })

    @agent.tool
    def product_stock(ctx: RunContext, product_name: str, size: Optional[str] = None) -> str:
        """Look up stock and inventory information from database.

        Use this when customer asks about availability, stock, or specific sizes.

        Args:
            product_name: Name or partial name of the product
            size: Optional size (S, M, L, XL, XS, XXL or natural names like "medium")

        Returns:
            JSON string with inventory details or not found message
        """
        result = _find_product_by_name(product_name)
        if not result:
            return json.dumps({"found": False, "message": f"Product '{product_name}' not found"})

        product_id = result["product_id"]
        product_name_db = result["name"]

        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.cursor()

            if size:
                normalized_size = _normalize_size(size)
                if not normalized_size:
                    return json.dumps({
                        "found": True,
                        "product_id": product_id,
                        "product_name": product_name_db,
                        "message": f"Cannot map size '{size}' to standard sizes (S, M, L, XL, XS, XXL)"
                    })

                # Look up specific size
                cursor.execute(
                    "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?",
                    (product_id, normalized_size)
                )
                inv_row = cursor.fetchone()
                quantity = inv_row[0] if inv_row else 0

                return json.dumps({
                    "found": True,
                    "product_id": product_id,
                    "product_name": product_name_db,
                    "requested_size": normalized_size,
                    "quantity": quantity,
                    "in_stock": quantity > 0,
                })

            # Return all sizes
            cursor.execute(
                "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY size",
                (product_id,)
            )
            inventory = cursor.fetchall()

            return json.dumps({
                "found": True,
                "product_id": product_id,
                "product_name": product_name_db,
                "all_sizes": [{"size": row[0], "quantity": row[1], "in_stock": row[1] > 0} for row in inventory],
            })
        finally:
            conn.close()

    @agent.tool
    def recommend_products(
        ctx: RunContext,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        size: Optional[str] = None,
    ) -> str:
        """Recommend real catalogue products matching budget/type/size constraints.

        Use this for requests like "Show me hoodies under $70" or
        "I need a hoodie under $70 in medium". Unlike search_products (plain
        keyword search), this tool enforces numeric/structural constraints:
        max_price is a hard ceiling, and if size is given, only products with
        quantity > 0 in that size are returned.

        Args:
            category: Product type/category keyword (e.g. "hoodie", "t-shirt")
            max_price: Maximum price in USD; products above this are excluded
            size: Optional size (S, M, L, XL, XS, XXL or natural names like "medium").
                  If given, only products with real inventory quantity > 0 in
                  that size are recommended.

        Returns:
            JSON string with up to 8 matching real products (product_id, name,
            price, short_description, image_file_path) or a message if none match.
        """
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.cursor()

            where_clauses = []
            params: list = []

            if category:
                cat = category.lower().strip()
                singular = cat[:-1] if cat.endswith('s') and len(cat) > 1 else cat
                where_clauses.append(
                    "(LOWER(garment_type) LIKE ? OR LOWER(garment_type) LIKE ? "
                    "OR LOWER(name) LIKE ? OR LOWER(name) LIKE ? "
                    "OR LOWER(search_tags) LIKE ? OR LOWER(search_tags) LIKE ?)"
                )
                params.extend([
                    f"%{cat}%", f"%{singular}%",
                    f"%{cat}%", f"%{singular}%",
                    f"%{cat}%", f"%{singular}%",
                ])

            if max_price is not None:
                where_clauses.append("price <= ?")
                params.append(max_price)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            if size:
                normalized_size = _normalize_size(size)
                if not normalized_size:
                    return json.dumps({
                        "found": False,
                        "products": [],
                        "message": f"Cannot map size '{size}' to standard sizes (S, M, L, XL, XS, XXL)"
                    })
                query = f"""
                    SELECT c.product_id, c.name, c.price, c.description, c.image_file_path
                    FROM catalogue c
                    JOIN inventory i ON c.product_id = i.product_id
                    {where_sql}{' AND' if where_sql else 'WHERE'} i.size = ? AND i.quantity > 0
                    ORDER BY c.price ASC
                    LIMIT 8
                """
                cursor.execute(query, (*params, normalized_size))
            else:
                query = f"""
                    SELECT product_id, name, price, description, image_file_path
                    FROM catalogue c
                    {where_sql}
                    ORDER BY price ASC
                    LIMIT 8
                """
                cursor.execute(query, params)

            results = cursor.fetchall()

            if not results:
                return json.dumps({
                    "found": False,
                    "products": [],
                    "message": "No products match those constraints."
                })

            products = []
            for row in results:
                desc = row[3] or ""
                short_desc = desc[:60] + "..." if len(desc) > 60 else desc
                products.append({
                    "product_id": row[0],
                    "name": row[1],
                    "price": row[2],
                    "short_description": short_desc,
                    "image_file_path": row[4],
                })

            # Flow recommendations through the same Problem 7 products channel
            # so the frontend renders them as the existing ProductCard grid -
            # no second/incompatible card system.
            if ctx is not None and hasattr(ctx, 'deps') and ctx.deps is not None:
                ctx.deps.products = products

            return json.dumps({
                "found": True,
                "products": products,
                "message": f"Found {len(products)} product(s) matching your criteria."
            })
        finally:
            conn.close()

    @agent.tool
    def check_variant_availability(
        ctx: RunContext,
        product_name: str,
        color: Optional[str] = None,
        size: Optional[str] = None,
    ) -> str:
        """Check a product's listed colors and real size-level stock.

        IMPORTANT SCHEMA LIMITATION: this database stores colors at the
        PRODUCT level (catalogue.colors, a JSON array) and stock quantity at
        the SIZE level (inventory.quantity), but it does NOT track quantity
        per color+size combination. This tool can truthfully confirm whether
        a color is listed for the product, and whether a size has stock, but
        it cannot report a quantity specific to one color+size pair. Do not
        claim a quantity is specific to a color - only to a size.

        Args:
            product_name: Name or partial name of the product
            color: Optional color to check against the product's listed colors
            size: Optional size (S, M, L, XL, XS, XXL or natural names)

        Returns:
            JSON string with found, requested_color, color_listed,
            requested_size, quantity, in_stock, and a schema_note.
        """
        result = _find_product_by_name(product_name)
        if not result:
            return json.dumps({"found": False, "message": f"Product '{product_name}' not found in database"})

        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT colors FROM catalogue WHERE product_id = ?", (result["product_id"],))
            colors_row = cursor.fetchone()
            listed_colors = json.loads(colors_row[0]) if colors_row and colors_row[0] else []

            color_listed = None
            if color:
                color_listed = any(color.strip().lower() == c.strip().lower() for c in listed_colors)

            response = {
                "found": True,
                "product_id": result["product_id"],
                "name": result["name"],
                "listed_colors": listed_colors,
                "requested_color": color,
                "color_listed": color_listed,
                "schema_note": (
                    "Colors are tracked per product, and stock quantity is tracked "
                    "per size - this database does not store stock separately by "
                    "color+size combination."
                ),
            }

            if size:
                normalized_size = _normalize_size(size)
                if not normalized_size:
                    response["requested_size"] = size
                    response["quantity"] = None
                    response["in_stock"] = None
                    response["message"] = f"Cannot map size '{size}' to standard sizes (S, M, L, XL, XS, XXL)"
                    return json.dumps(response)

                cursor.execute(
                    "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?",
                    (result["product_id"], normalized_size)
                )
                inv_row = cursor.fetchone()
                quantity = inv_row[0] if inv_row else 0

                response["requested_size"] = normalized_size
                response["quantity"] = quantity
                response["in_stock"] = quantity > 0

            return json.dumps(response)
        finally:
            conn.close()
