# Problem 9 — Usability Improvements

Four improvements: two front-end, two agent/backend. All four are implemented and running in the actual application (not mockups).

---

## 1. Frontend Improvement 1 — Product Discovery Filters

### WHAT WAS ADDED

The existing Products page (`frontend/src/pages/Products.tsx`) now has, alongside the original text search:

- **Category filter** — a dropdown grouping the real `catalogue.garment_type` values into shopper-friendly buckets (Hoodies, T-Shirts, Jackets, Quarter-Zips, Crewnecks & Sweatshirts, Performance Shirts, Other). Only categories with at least one real matching product appear.
- **Max price filter** — a slider grounded in the real min/max price range of the loaded catalogue (`$32`–`$98`), not an arbitrary scale.
- **Availability filter** — "All" vs "In Stock", backed by a new `in_stock` boolean computed server-side as `SUM(inventory.quantity) > 0` per product (`GET /api/products`).
- All filters (plus the existing text search and URL `?filter=` param) combine with AND logic, update instantly client-side with no page reload, show a live result count ("N products"), display active-filter badges, and offer a one-click **Clear Filters** control. An empty-result state with its own Clear Filters button appears when no product matches.

### WHY IT HELPS

Campus Customs' catalogue has 102 products spanning 21 raw garment-type strings and a $32–$98 price range. Before this change, a shopper could only text-search by name/description — there was no way to narrow by type, budget, or stock. A parent buying a gift ("show me hoodies under $70 that are in stock") previously had to scroll the entire catalogue. Filters reduce browsing friction, help shoppers reach a purchase decision faster, and reduce support/chat load for basic "what do you have under $X" questions since the shopper can self-serve on the Products page directly.

---

## 2. Frontend Improvement 2 — Chat Experience Improvements

### WHAT WAS ADDED

`frontend/src/components/ChatWidget.tsx` now includes:

- A **"Campus Customs is thinking..."** animated indicator bubble shown while waiting for `/api/chat`, so the shopper knows the request is in flight.
- **Duplicate-send prevention**: the input textarea and Send button are both disabled while a request is pending, and the Enter-key handler is guarded the same way, so a shopper can't fire overlapping requests by hammering Enter/click.
- A **"Clear chat"** header control that resets the *current visible* conversation and dismisses any shown product cards. For logged-in shoppers this does not delete their persisted `chat_messages` rows — reloading or navigating away and back still restores their saved history (Problem 8 persistence is untouched), so the control's behavior matches its label honestly.
- A **dismiss (✕) control** on the dynamic product-results panel (carried over from Problem 7, kept and documented here), plus the existing behavior that a new search's results replace the old set and an empty search result clears stale cards.
- Restored Problem 8 history keeps the existing distinct user/assistant message styling (different background colors/alignment), so a returning shopper can visually tell who said what, and restored product cards remain normal clickable `ProductCard` links to `/products/:productId`.

### WHY IT HELPS

Shoppers abandon chat widgets that appear frozen or that silently accept multiple duplicate clicks (common cause of repeated/garbled replies). A visible "thinking" state and disabled inputs make the assistant feel responsive and trustworthy. A low-risk "Clear chat" button lets a shopper tidy up their screen (e.g., after a long browsing session) without fear of losing their saved history, which keeps the widget usable in long sessions and avoids a support complaint like "I accidentally deleted my conversation."

---

## 3. Agent/Backend Improvement 1 — Grounded Recommendations

### WHAT WAS ADDED

A new PydanticAI tool, `recommend_products(ctx, category, max_price, size)` (`backend/tools.py`), registered the same way as the Problem 6/7 tools via `@agent.tool` with `RunContext`. It answers constrained requests like *"Show me hoodies under $70"*, *"Find me a T-shirt under $40"*, or *"I need a hoodie under $70 in medium"*:

- `max_price` is a hard SQL `WHERE price <= ?` filter — never a soft suggestion.
- `category` matches real `garment_type`/`name`/`search_tags` (plural/singular tolerant).
- If `size` is given, the query joins `inventory` and requires `quantity > 0` for that size — a recommendation is never shown for a size that's actually out of stock.
- Returns up to 8 products, read-only, parameterized SQL.
- Recommendations flow through the exact same `ChatDeps.products` → `ChatResponse.products` channel as Problem 7's `search_products`, so the frontend renders them with the existing `ProductCard` grid — no second/incompatible card system was built.

### WHY IT HELPS

Plain keyword search (Problem 7) can't express "under $70" or "in medium" — it would either ignore the constraint or require the shopper to manually check each result. A grounded recommendation tool lets the chatbot act like a helpful in-store associate working within the shopper's actual budget and size, which increases the chance a shown product is one the shopper can actually buy right now — reducing cart abandonment caused by "I found something I liked but it's out of my size/budget."

---

## 4. Agent/Backend Improvement 2 — Variant Availability

### WHAT WAS ADDED

A new PydanticAI tool, `check_variant_availability(ctx, product_name, color, size)` (`backend/tools.py`), for questions combining color + size + availability, e.g. *"Do you have the Basic Hoodie Big Yale in navy, medium?"*. It checks the product's real `catalogue.colors` JSON array for the requested color and the real `inventory.quantity` for the requested size, and returns both facts with an explicit `schema_note`.

**Real schema limitation, stated honestly rather than hidden**: this database tracks color at the *product* level and quantity at the *size* level — there is no combined color+size stock count. The tool and the updated system prompt (`backend/prompts/prompt.md`) both make this explicit, so the agent reports "navy is a listed color, and there are 5 units in size M overall" rather than fabricating a quantity specific to the navy+medium combination. If a requested color isn't in the product's real color list, the tool says so plainly instead of guessing; a size with `quantity = 0` is reported as out of stock.

### WHY IT HELPS

Shoppers naturally ask "do you have it in [color] and [size]" as a single question, but a chatbot that just stitches together price/stock facts can easily overclaim precision the data doesn't support (e.g., implying there are exactly 5 navy mediums when the database can't actually prove that). Being explicit about what the database can and can't confirm prevents the business from making a promise (via the chatbot) that inventory can't back up — avoiding frustrated customers who show up expecting a specific color/size combination that was never actually tracked.
