
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Literal, Dict, Any


@dataclass
class PricingItemInput:
    """
    Normalized representation of a single pricing line item.
    """
    description: str
    quantity: float = 1.0
    unit: str = "unit"
    category: Literal["labour", "materials", "equipment", "other"] = "other"
    base_unit_cost: float = 0.0
    risk_level: Literal["low", "medium", "high"] = "medium"
    notes: Optional[str] = None

    cost_basis_hint: Optional[str] = None
    escalation_hint: Optional[str] = None


def analyze_pricing_spec_text(
    spec_text: str,
    tender_type: str = "unknown",
) -> Dict[str, Any]:
    """
    Lightweight heuristic analysis of a pricing / BOQ specification.
    """
    text = spec_text.lower()

    def flag(pattern: str) -> bool:
        return bool(re.search(pattern, text))

    flags = {
        "mentions_firm_price": flag(r"firm price"),
        "mentions_non_firm_price": flag(r"non[-\s]?firm"),
        "mentions_escalation": flag(r"escalat(e|ion)"),
        "mentions_vat_inclusive": flag(r"vat\s*(inclusive|incl\b)"),
        "mentions_vat_exclusive": flag(r"vat\s*(exclusive|excl\b)"),
        "mentions_provisional_sums": flag(r"provisional sum"),
        "mentions_prime_costs": flag(r"prime cost"),
        "mentions_dayworks": flag(r"daywork"),
        "mentions_rate_only_items": flag(r"rate only"),
        "mentions_lumpsum": flag(r"lump\s*sum"),
        "mentions_discounts": flag(r"discount"),
    }

    currency = None
    if " zar" in text or "south african rand" in text or "r " in text or " r" in text:
        currency = "ZAR"
    elif " usd" in text or "dollar" in text:
        currency = "USD"
    elif " eur" in text or "euro" in text:
        currency = "EUR"

    line_candidates = [
        ln for ln in spec_text.splitlines()
        if re.search(r"\d", ln) and len(ln.strip()) > 10
    ]

    summary = (
        f"The pricing specification appears to describe approximately "
        f"{len(line_candidates)} line items containing numeric values. "
    )

    if tender_type == "public":
        summary += (
            "The tender is flagged as PUBLIC – ensure compliance with "
            "PPPFA, MFMA / PFMA and any prescribed pricing schedules."
        )
    elif tender_type == "private":
        summary += (
            "The tender is flagged as PRIVATE – commercial flexibility "
            "may be higher but still ensure clear assumptions."
        )

    return {
        "summary": summary,
        "flags": flags,
        "detected_currency": currency,
        "estimated_numeric_lines": len(line_candidates),
    }


def _risk_multiplier(risk_level: str, strategy: str) -> float:
    base = {
        "low": 1.00,
        "medium": 1.05,
        "high": 1.10,
    }.get(risk_level, 1.05)

    if strategy == "low_cost":
        base -= 0.02
    elif strategy == "premium":
        base += 0.03

    return max(base, 0.90)


def build_pricing_table(
    typed_items: List[PricingItemInput],
    strategy: str,
    overhead_pct: float,
    profit_margin_pct: float,
    contingency_pct: float,
    tax_rate_pct: float,
    currency_symbol: str,
) -> Dict[str, Any]:
    line_items_output: List[Dict[str, Any]] = []
    subtotal_direct_cost = 0.0

    for idx, item in enumerate(typed_items, start=1):
        risk_mult = _risk_multiplier(item.risk_level, strategy)
        effective_unit_cost = item.base_unit_cost * risk_mult
        direct_cost = effective_unit_cost * item.quantity

        subtotal_direct_cost += direct_cost

        line_items_output.append({
            "line_no": idx,
            "description": item.description,
            "quantity": item.quantity,
            "unit": item.unit,
            "category": item.category,
            "risk_level": item.risk_level,
            "base_unit_cost": round(item.base_unit_cost, 2),
            "effective_unit_cost": round(effective_unit_cost, 2),
            "line_total_excl_markups": round(direct_cost, 2),
            "notes": item.notes,
            "cost_basis_hint": item.cost_basis_hint,
            "escalation_hint": item.escalation_hint,
        })

    overhead_amount = subtotal_direct_cost * (overhead_pct / 100.0)
    contingency_amount = subtotal_direct_cost * (contingency_pct / 100.0)
    profit_base = subtotal_direct_cost + overhead_amount + contingency_amount
    profit_amount = profit_base * (profit_margin_pct / 100.0)

    total_excl_tax = (
        subtotal_direct_cost +
        overhead_amount +
        contingency_amount +
        profit_amount
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
        "line_items": line_items_output,
        "totals": totals,
    }


def render_pricing_report_html(
    tender_context: Dict[str, Any],
    company_context: Dict[str, Any],
    pricing_model: Dict[str, Any],
    additional_notes: Optional[str] = None,
) -> str:
    tender_title = tender_context.get("tender_title") or "Tender Pricing Proposal"
    tender_reference = tender_context.get("tender_reference") or ""
    tender_type = tender_context.get("tender_type") or "unknown"

    company_name = company_context.get("company_name") or company_context.get("trading_name") or "Your Company"
    trading_name = company_context.get("trading_name") or ""
    reg_no = company_context.get("registration_number") or ""
    vat_no = company_context.get("vat_number") or ""
    bbbee = company_context.get("bbbee_level") or ""
    contact_person = company_context.get("contact_person") or ""
    contact_email = company_context.get("contact_email") or ""
    contact_phone = company_context.get("contact_phone") or ""
    address = company_context.get("address") or ""

    strategy = pricing_model.get("strategy")
    line_items = pricing_model.get("line_items", [])
    totals = pricing_model.get("totals", {})
    currency = totals.get("currency_symbol", "R")

    overhead_pct = totals.get("overhead_pct")
    contingency_pct = totals.get("contingency_pct")
    profit_margin_pct = totals.get("profit_margin_pct")
    tax_rate_pct = totals.get("tax_rate_pct")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Pricing Proposal – {tender_title}</title>
  <style>
    :root {{
      --bg: #f9fafb;
      --card-bg: #ffffff;
      --border: #e5e7eb;
      --text-main: #111827;
      --text-muted: #6b7280;
      --accent: #2563eb;
      --accent-soft: #dbeafe;
      --danger: #b91c1c;
      --table-header: #f3f4f6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 2rem;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
                   sans-serif;
      background: var(--bg);
      color: var(--text-main);
    }}
    .report {{
      max-width: 960px;
      margin: 0 auto;
      background: var(--card-bg);
      border-radius: 0.75rem;
      border: 1px solid var(--border);
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
      padding: 2.5rem 2.75rem;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 2rem;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
    }}
    .brand h1 {{
      font-size: 1.6rem;
      margin: 0 0 0.35rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .brand span {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.9rem;
      color: var(--accent);
      background: var(--accent-soft);
      padding: 0.15rem 0.6rem;
      border-radius: 999px;
      font-weight: 500;
    }}
    .meta {{
      font-size: 0.9rem;
      text-align: right;
      color: var(--text-muted);
    }}
    .section-title {{
      font-size: 1rem;
      font-weight: 600;
      margin: 0 0 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 1.75rem;
      margin-bottom: 2rem;
    }}
    .card {{
      border-radius: 0.75rem;
      border: 1px solid var(--border);
      padding: 1.25rem 1.5rem;
      background: #ffffff;
    }}
    .card p {{
      margin: 0.1rem 0;
      font-size: 0.9rem;
    }}
    .label {{
      font-weight: 500;
      color: var(--text-muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.75rem;
      font-size: 0.9rem;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 0.4rem 0.5rem;
      vertical-align: top;
    }}
    th {{
      background: var(--table-header);
      text-align: left;
      font-weight: 600;
      font-size: 0.85rem;
    }}
    td.numeric {{
      text-align: right;
      white-space: nowrap;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 0.15rem 0.5rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 500;
    }}
    .badge.risk-low {{
      background: #ecfdf3;
      color: #166534;
    }}
    .badge.risk-medium {{
      background: #fef9c3;
      color: #854d0e;
    }}
    .badge.risk-high {{
      background: #fef2f2;
      color: #b91c1c;
    }}
    .totals {{
      margin-top: 1.25rem;
      max-width: 340px;
      margin-left: auto;
      font-size: 0.9rem;
    }}
    .totals-row {{
      display: flex;
      justify-content: space-between;
      padding: 0.3rem 0;
    }}
    .totals-row.label {{
      color: var(--text-muted);
    }}
    .totals-row.strong {{
      font-weight: 600;
      border-top: 1px solid var(--border);
      margin-top: 0.4rem;
      padding-top: 0.6rem;
    }}
    .note {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.25rem;
    }}
    .chip {{
      font-size: 0.75rem;
      padding: 0.1rem 0.55rem;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--text-muted);
    }}
    .footer-notes {{
      margin-top: 2.25rem;
      padding-top: 1.5rem;
      border-top: 1px dashed var(--border);
      font-size: 0.9rem;
    }}
    .footer-notes h3 {{
      margin-top: 0;
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--text-muted);
    }}
    .footer-notes p {{
      margin: 0.25rem 0;
    }}
    @media print {{
      body {{
        padding: 0;
        background: #ffffff;
      }}
      .report {{
        box-shadow: none;
        border-radius: 0;
      }}
    }}
  </style>
</head>
<body>
  <div class="report">
    <header>
      <div class="brand">
        <h1>{company_name}</h1>
        <span>Tri‑Tender Pricing Proposal</span>
        <div style="margin-top: 0.4rem; font-size: 0.85rem; color: var(--text-muted);">
          {trading_name if trading_name else ""}{' • ' if trading_name and reg_no else ''}{f'Reg: {reg_no}' if reg_no else ''}
        </div>
      </div>
      <div class="meta">
        <div><strong>{tender_title}</strong></div>
        {f'<div>Reference: {tender_reference}</div>' if tender_reference else ''}
        <div>Type: {tender_type.title()}</div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2 class="section-title">Client & Tender</h2>
        <p><span class="label">Tender:</span> {tender_title}</p>
        {f'<p><span class="label">Reference:</span> {tender_reference}</p>' if tender_reference else ''}
        <p><span class="label">Type:</span> {tender_type.title()}</p>
        <p><span class="label">Prepared by:</span> {company_name}</p>
      </div>
      <div class="card">
        <h2 class="section-title">Contact Details</h2>
        {f'<p><span class="label">Contact person:</span> {contact_person}</p>' if contact_person else ''}
        {f'<p><span class="label">Email:</span> {contact_email}</p>' if contact_email else ''}
        {f'<p><span class="label">Phone:</span> {contact_phone}</p>' if contact_phone else ''}
        {f'<p><span class="label">Address:</span> {address}</p>' if address else ''}
        <div class="chips">
          {f'<span class="chip">VAT: {vat_no}</span>' if vat_no else ''}
          {f'<span class="chip">B-BBEE Level {bbbee}</span>' if bbbee else ''}
        </div>
      </div>
    </section>

    <section>
      <h2 class="section-title">Pricing Summary</h2>
      <div class="card">
        <p style="margin-bottom: 0.75rem;">
          The pricing below has been prepared on a
          <strong>{strategy.replace('_', ' ').title()}</strong> basis,
          with transparent allocation of direct costs, overheads,
          profit margin and tax.
        </p>
        <div class="chips">
          <span class="chip">Overheads: {overhead_pct:.1f}%</span>
          <span class="chip">Contingency: {contingency_pct:.1f}%</span>
          <span class="chip">Profit margin: {profit_margin_pct:.1f}%</span>
          <span class="chip">Tax: {tax_rate_pct:.1f}%</span>
        </div>

        <table>
          <thead>
            <tr>
              <th style="width: 3rem;">#</th>
              <th>Description</th>
              <th style="width: 4rem;">Qty</th>
              <th style="width: 4rem;">Unit</th>
              <th style="width: 4.5rem;">Category</th>
              <th style="width: 5rem;">Risk</th>
              <th style="width: 6.5rem;">Unit Cost</th>
              <th style="width: 7rem;">Line Total</th>
            </tr>
          </thead>
          <tbody>
"""

    for item in line_items:
        risk = (item.get("risk_level") or "medium").lower()
        risk_class = f"risk-{risk}"
        unit_cost = item.get("effective_unit_cost", item.get("base_unit_cost", 0.0))
        line_total = item.get("line_total_excl_markups", 0.0)
        notes = item.get("notes") or item.get("cost_basis_hint") or ""
        notes_html = f"<div class='note'>{notes}</div>" if notes else ""

        html += f"""
            <tr>
              <td>{item.get('line_no')}</td>
              <td>
                {item.get('description', '')}
                {notes_html}
              </td>
              <td class="numeric">{item.get('quantity')}</td>
              <td>{item.get('unit')}</td>
              <td>{item.get('category').title() if item.get('category') else ''}</td>
              <td>
                <span class="badge {risk_class}">
                  {risk.title()}
                </span>
              </td>
              <td class="numeric">{currency} {unit_cost:,.2f}</td>
              <td class="numeric">{currency} {line_total:,.2f}</td>
            </tr>
        """

    subtotal = totals.get("subtotal_direct_cost", 0.0)
    overhead_amount = totals.get("overhead_amount", 0.0)
    contingency_amount = totals.get("contingency_amount", 0.0)
    profit_amount = totals.get("profit_amount", 0.0)
    total_excl_tax = totals.get("total_excl_tax", 0.0)
    tax_amount = totals.get("tax_amount", 0.0)
    total_incl_tax = totals.get("total_incl_tax", 0.0)

    html += f"""
          </tbody>
        </table>

        <div class="totals">
          <div class="totals-row label">
            <span>Direct cost subtotal</span>
            <span>{currency} {subtotal:,.2f}</span>
          </div>
          <div class="totals-row label">
            <span>Overheads ({overhead_pct:.1f}%)</span>
            <span>{currency} {overhead_amount:,.2f}</span>
          </div>
          <div class="totals-row label">
            <span>Contingency ({contingency_pct:.1f}%)</span>
            <span>{currency} {contingency_amount:,.2f}</span>
          </div>
          <div class="totals-row label">
            <span>Profit margin ({profit_margin_pct:.1f}%)</span>
            <span>{currency} {profit_amount:,.2f}</span>
          </div>
          <div class="totals-row strong">
            <span>Total excl. tax</span>
            <span>{currency} {total_excl_tax:,.2f}</span>
          </div>
          <div class="totals-row label">
            <span>Tax ({tax_rate_pct:.1f}%)</span>
            <span>{currency} {tax_amount:,.2f}</span>
          </div>
          <div class="totals-row strong">
            <span>Total incl. tax</span>
            <span>{currency} {total_incl_tax:,.2f}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="footer-notes">
      <h3>Notes & Qualifications</h3>
    """

    if additional_notes:
        html += f"<p>{additional_notes}</p>"
    else:
        html += (
            "<p>This pricing proposal is based on information available at the "
            "time of preparation. It assumes normal working conditions, "
            "uninterrupted access to site, and that all statutory "
            "requirements and third-party approvals are in place.</p>"
            "<p>Unless explicitly stated otherwise, prices are subject to "
            "final contract terms, scope confirmation and any escalation "
            "provisions prescribed in the tender documentation.</p>"
        )

    html += """
    </section>
  </div>
</body>
</html>
"""

    return html
