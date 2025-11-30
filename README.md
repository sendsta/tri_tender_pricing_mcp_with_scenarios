# Tri‑Tender Pricing MCP

A professional public & private tender pricing MCP server for the Tri‑Tender
ecosystem, built with FastMCP and fastmcp-http.

This server:

- Works with **tender-docs-mcp-file-resource** (or any parsing MCP) to consume
  structured pricing requirements.
- Provides transparent pricing calculations for **public** and **private**
  tenders (direct cost, overheads, contingency, profit, tax).
- Produces a clean, styled **HTML pricing report** that can be converted to PDF.
- Is deployable on **FastMCP Cloud** using a simple `server.py` HTTP entrypoint.

## Project structure

```text
tender_pricing_mcp/
  ├─ server.py             # FastMCP HTTP server & tool definitions
  ├─ pricing_engine.py     # Core pricing models & HTML renderer
  ├─ requirements.txt      # Python dependencies
  └─ README.md             # This file
```

## Tools

### 1. `pricing_entrypoint`

Starting point for any pricing workflow.

- If `pricing_requirements` are **missing**:
  - Returns `status="missing_pricing_spec"`.
  - Instructs the client LLM to:
    1. Ask the user to upload the pricing schedule / BOQ.
    2. Call `tender-docs-mcp-file-resource` to parse it.
    3. Call `pricing_entrypoint` again with `pricing_requirements` filled.

- If `pricing_requirements` **are present**:
  - Optionally analyses raw `parsed_pricing_spec_text`.
  - Returns `status="ready_for_pricing_model"` plus context.

### 2. `build_pricing_model`

Accepts a list of pricing items (mapped to `PricingItemInput`) and returns:

- Per-line breakdown with risk‑adjusted unit cost and direct cost.
- Overall totals, including overheads, contingency, profit and tax.

### 3. `generate_pricing_report_html`

Renders a fully styled HTML report from:

- `tender_context`
- `company_context`
- `pricing_model` (from `build_pricing_model`)
- `additional_notes` (optional text for qualifications / exclusions)

Output:

```jsonc
{
  "html": "<!doctype html> ...",
  "metadata": {
    "tender_context": { ... },
    "company_context": { ... },
    "generated_at": "2025-11-30T09:00:00+00:00"
  }
}
```

The HTML uses inline CSS and is PDF‑friendly.

## FastMCP Cloud deployment

1. Create a new project on **FastMCP Cloud** and link it to this code (GitHub
   repo or ZIP upload).

2. Set the **entrypoint** to:

   ```text
   server.py
   ```

3. Ensure the build installs dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. FastMCP Cloud usually provides a `PORT` env var; `server.py` reads it and
   runs the HTTP MCP server on `0.0.0.0:<PORT>`.

## Local testing

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Then add the resulting HTTP MCP endpoint to your MCP client (Tri‑Tender app,
Claude Desktop, Cursor, etc.).


### 4. `compare_pricing_scenarios`

Runs side-by-side **what-if** comparisons for different strategies
(`low_cost`, `balanced`, `premium`) using the same engine as `build_pricing_model`.

Example call:

```jsonc
tri-tender-pricing-mcp__compare_pricing_scenarios({
  "pricing_items": [...],
  "strategies": ["low_cost", "balanced", "premium"],
  "overhead_pct": 15,
  "profit_margin_pct": 20,
  "contingency_pct": 5,
  "tax_rate_pct": 15,
  "currency_symbol": "R"
})
```

The response contains a `scenarios` object (full pricing model per strategy)
and a `comparison.by_strategy` array with headline numbers you can show in the UI.
