# Campus Customs — Yale Merchandise Shop + AI Shopping Assistant

A full-stack e-commerce storefront for Yale-branded merchandise, built with FastAPI + PydanticAI (backend) and React/Vite/TypeScript (frontend). Includes an AI shopping assistant grounded in a real SQLite product catalogue.

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Node.js 18+ and npm
- A Portkey API key (for the `gpt-4o-mini` model via the Portkey gateway)

## 1. Local Data Pack (not included in this repository)

This repository intentionally does **not** include the product database or images. Before running the app, place the provided data pack at the project root:

```
data/
├── campus_customs.db
└── products/
    └── (102 product images)
```

## 2. Environment Setup

Copy the example environment file and fill in your own key:

```bash
cp .env.example .env
```

Required variable:

- `PORTKEY_API_KEY` — your Portkey API key (never commit the real value)

## 3. Backend Setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cd backend
# Set PORTKEY_API_KEY in your shell, or load it from the .env at the project root
uvicorn main:app --reload --port 8000
```

The backend serves **all** endpoints (products, auth, images, chat) from this single process on port 8000.

## 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Vite will print the local URL (typically `http://localhost:5173`). Open it in your browser — the frontend is already configured to talk to the backend at `http://localhost:8000`.

## What the App Does

- **Product browsing**: catalogue grid with real images, prices, and descriptions (`/products`, `/products/:id`)
- **Authentication**: account creation and login (bcrypt / PBKDF2-compatible, seeded test account included in the data pack)
- **AI chat assistant**: a PydanticAI agent (via Portkey → `gpt-4o-mini`) grounded entirely in the real database — never invents prices, stock, or colors
- **Product search & recommendations**: natural-language catalogue search and budget/size-constrained recommendations, rendered as live product cards in the chat
- **Customer memory**: logged-in shoppers get persistent chat history and page-aware context (e.g. "do you have *this* in pink?")
- **Discovery filters**: category, price, and availability filters on the Products page
- **Audit trail**: every real agent/tool call is appended (never overwritten) to `output/audit_trail.json` for transparency

## Project Documentation

See `output/harness.md` for full system architecture, model fields, tools, safety rules, and specs. See `output/design.md` and `output/usability.md` for design/UX rationale, and `output/app_check.html` for live-application verification screenshots. `AI_prompts.md` logs every development prompt used to build this project (Problems 1–13).
