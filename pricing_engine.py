
from dataclasses import dataclass
from typing import Optional, Literal, List, Dict, Any


@dataclass
class PricingItemInput:
    description: str
    quantity: float = 1.0
    unit: str = "unit"
    category: Literal["labour", "materials", "equipment", "other"] = "other"
    base_unit_cost: float = 0.0
    risk_level: Literal["low", "medium", "high"] = "medium"
    notes: Optional[str] = None
    cost_basis_hint: Optional[str] = None
    escalation_hint: Optional[str] = None


def _risk_multiplier(risk_level: str, strategy: str) -> float:
    base = {"low": 1.0, "medium": 1.05, "high": 1.1}.get(risk_level, 1.05)
    if strategy == "low_cost":
        return base * 0.97
    if strategy == "premium":
        return base * 1.05
    return base


def analyze_pricing_spec_text(text: str, tender_type: str = "unknown") -> Dict[str, Any]:
    """
    Very simple heuristic analysis. In your real repo you can expand this.
    """
    lower = text.lower()
    flags = []
    currency = "R"
    if "usd" in lower or "dollar" in lower:
        currency = "$"
        flags.append("Possible USD currency mentioned.")
    if "firm for" in lower or "no escalation" in lower:
        flags.append("Firm pricing / no escalation mentioned.")
    if "escalation" in lower and "cpi" in lower:
        flags.append("CPI-based escalation mentioned.")
    return {
        "currency": currency,
        "flags": flags,
        "tender_type": tender_type,
    }


def build_pricing_table(
    typed_items: List[PricingItemInput],
    strategy: str,
    overhead_pct: float,
    profit_margin_pct: float,
    contingency_pct: float,
    tax_rate_pct: float,
    currency_symbol: str,
) -> Dict[str, Any]:
    line_items = []
    subtotal_direct_cost = 0.0

    for idx, item in enumerate(typed_items, start=1):
        mult = _risk_multiplier(item.risk_level, strategy)
        effective_unit_cost = item.base_unit_cost * mult
        line_total = effective_unit_cost * item.quantity
        subtotal_direct_cost += line_total

        line_items.append(
            {
                "line_no": idx,
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "risk_level": item.risk_level,
                "base_unit_cost": round(item.base_unit_cost, 2),
                "effective_unit_cost": round(effective_unit_cost, 2),
                "line_total_excl_markups": round(line_total, 2),
                "notes": item.notes,
                "cost_basis_hint": item.cost_basis_hint,
                "escalation_hint": item.escalation_hint,
            }
        )

    overhead_amount = subtotal_direct_cost * (overhead_pct / 100.0)
    contingency_amount = subtotal_direct_cost * (contingency_pct / 100.0)
    profit_amount = (subtotal_direct_cost + overhead_amount + contingency_amount) * (
        profit_margin_pct / 100.0
    )
    total_excl_tax = (
        subtotal_direct_cost + overhead_amount + contingency_amount + profit_amount
    )
    tax_amount = total_excl_tax * (tax_rate_pct / 100.0)
    total_incl_tax = total_excl_tax + tax_amount

    totals = {
        "currency_symbol": currency_symbol,
        "subtotal_direct_cost": round(subtotal_direct_cost, 2),
        "overhead_pct": overhead_pct,
        "overhead_amount": round(overhead_amount, 2),
        "contingency_pct": contingency_pct,
        "contingency_amount": round(contingency_amount, 2),
        "profit_margin_pct": profit_margin_pct,
        "profit_amount": round(profit_amount, 2),
        "tax_rate_pct": tax_rate_pct,
        "tax_amount": round(tax_amount, 2),
        "total_excl_tax": round(total_excl_tax, 2),
        "total_incl_tax": round(total_incl_tax, 2),
    }

    return {
        "strategy": strategy,
        "inputs": {
            "overhead_pct": overhead_pct,
            "profit_margin_pct": profit_margin_pct,
            "contingency_pct": contingency_pct,
            "tax_rate_pct": tax_rate_pct,
            "currency_symbol": currency_symbol,
        },
        "line_items": line_items,
        "totals": totals,
    }


def render_pricing_report_html(
    tender_context: Dict[str, Any],
    company_context: Dict[str, Any],
    pricing_model: Dict[str, Any],
    additional_notes: Optional[str] = None,
) -> str:
    currency = pricing_model.get("totals", {}).get("currency_symbol", "R")
    totals = pricing_model.get("totals", {})
    line_items = pricing_model.get("line_items", [])
    tender_title = tender_context.get("tender_title") or ""
    tender_reference = tender_context.get("tender_reference") or ""
    company_name = company_context.get("company_name") or ""

    rows_html = ""
    for item in line_items:
        rows_html += f"""
        <tr>
          <td>{item['line_no']}</td>
          <td>{item['description']}</td>
          <td>{item['quantity']}</td>
          <td>{item['unit']}</td>
          <td>{item['category']}</td>
          <td>{item['risk_level'].title()}</td>
          <td style='text-align:right;'>{currency} {item['effective_unit_cost']:.2f}</td>
          <td style='text-align:right;'>{currency} {item['line_total_excl_markups']:.2f}</td>
        </tr>
        """

    notes_block = (
        f"<p>{additional_notes}</p>" if additional_notes else "<p>No additional notes.</p>"
    )

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Pricing Report - {company_name}</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 24px;
      background: #f9fafb;
      color: #111827;
    }}
    .card {{
      background: #ffffff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 10px 15px -3px rgba(15,23,42,0.08),
                  0 4px 6px -4px rgba(15,23,42,0.10);
    }}
    h1, h2, h3 {{
      margin-top: 0;
      color: #0b1120;
    }}
    .header-grid {{
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 16px;
      margin-bottom: 24px;
    }}
    .muted {{
      color: #6b7280;
      font-size: 0.875rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      font-size: 0.875rem;
    }}
    th, td {{
      border-bottom: 1px solid #e5e7eb;
      padding: 8px 6px;
      vertical-align: top;
    }}
    th {{
      text-align: left;
      background: #f3f4f6;
      font-weight: 600;
      color: #374151;
    }}
    .totals {{
      margin-top: 24px;
      max-width: 360px;
      margin-left: auto;
      font-size: 0.9rem;
    }}
    .totals-row {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }}
    .totals-row strong {{
      font-weight: 600;
    }}
    .totals-row.total {{
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #e5e7eb;
      font-size: 1rem;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.7rem;
      background: #e5e7eb;
      color: #374151;
      margin-left: 4px;
    }}
    .badge-public {{
      background: #dbeafe;
      color: #1d4ed8;
    }}
    .badge-private {{
      background: #dcfce7;
      color: #15803d;
    }}
    .notes {{
      margin-top: 24px;
      font-size: 0.9rem;
      color: #4b5563;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header-grid">
      <div>
        <h1>Pricing Proposal</h1>
        <p class="muted">
          <strong>Company:</strong> {company_name}<br/>
          <strong>Tender Title:</strong> {tender_title}<br/>
          <strong>Reference:</strong> {tender_reference}
        </p>
      </div>
      <div style="text-align:right;">
        <h3>Summary</h3>
        <div class="muted">
          <div>Total (excl. tax): <strong>{currency} {totals.get('total_excl_tax', 0):.2f}</strong></div>
          <div>Tax ({totals.get('tax_rate_pct', 0):.0f}%): <strong>{currency} {totals.get('tax_amount', 0):.2f}</strong></div>
          <div>Total (incl. tax): <strong>{currency} {totals.get('total_incl_tax', 0):.2f}</strong></div>
        </div>
      </div>
    </div>

    <h2>Pricing Breakdown</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Description</th>
          <th>Qty</th>
          <th>Unit</th>
          <th>Category</th>
          <th>Risk</th>
          <th style="text-align:right;">Unit Cost</th>
          <th style="text-align:right;">Line Total</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>

    <div class="totals">
      <div class="totals-row">
        <span>Direct cost subtotal</span>
        <span>{currency} {totals.get('subtotal_direct_cost', 0):.2f}</span>
      </div>
      <div class="totals-row">
        <span>Overheads ({totals.get('overhead_pct', 0):.0f}%)</span>
        <span>{currency} {totals.get('overhead_amount', 0):.2f}</span>
      </div>
      <div class="totals-row">
        <span>Contingency ({totals.get('contingency_pct', 0):.0f}%)</span>
        <span>{currency} {totals.get('contingency_amount', 0):.2f}</span>
      </div>
      <div class="totals-row">
        <span>Profit ({totals.get('profit_margin_pct', 0):.0f}%)</span>
        <span>{currency} {totals.get('profit_amount', 0):.2f}</span>
      </div>
      <div class="totals-row total">
        <strong>Total excl. tax</strong>
        <strong>{currency} {totals.get('total_excl_tax', 0):.2f}</strong>
      </div>
      <div class="totals-row">
        <span>Tax ({totals.get('tax_rate_pct', 0):.0f}%)</span>
        <span>{currency} {totals.get('tax_amount', 0):.2f}</span>
      </div>
      <div class="totals-row total">
        <strong>Total incl. tax</strong>
        <strong>{currency} {totals.get('total_incl_tax', 0):.2f}</strong>
      </div>
    </div>

    <div class="notes">
      <h3>Notes &amp; Qualifications</h3>
      {notes_block}
    </div>
  </div>
</body>
</html>
"""
    return html
