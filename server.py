
import os
from typing import List, Optional, Literal, Dict, Any

from fastmcp import FastMCP

from pricing_engine import (
    PricingItemInput,
    analyze_pricing_spec_text,
    build_pricing_table,
    render_pricing_report_html,
)

mcp = FastMCP(
    "tri-tender-pricing-mcp",
    description=(
        "Public & private tender pricing engine for Tri-Tender. "
        "Works with tender-docs-mcp-file-resource to turn parsed pricing "
        "requirements into a styled HTML pricing report and scenario analysis."
    ),
)


@mcp.tool
def pricing_entrypoint(
    tender_id: str,
    tender_title: Optional[str] = None,
    tender_reference: Optional[str] = None,
    tender_type: Literal["public", "private", "unknown"] = "unknown",
    pricing_requirements: Optional[List[Dict[str, Any]]] = None,
    parsed_pricing_spec_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Entrypoint for the Tri-Tender Pricing MCP.

    This tool:
    - Checks whether structured pricing_requirements are already available
      from a parsing MCP (e.g. tender-docs-mcp-file-resource).
    - If NOT available, it:
      * Returns status="missing_pricing_spec"
      * Instructs the client LLM to:
          1) Ask the user to upload the pricing schedule / BOQ section.
          2) Call tender-docs-mcp-file-resource to parse the pricing spec.
          3) Call this tool again with pricing_requirements populated.
    - If pricing_requirements ARE available, it:
      * Optionally analyzes parsed_pricing_spec_text for flags & notes.
      * Returns status="ready_for_pricing_model" plus normalized context.
    """
    tender_context = {
        "tender_id": tender_id,
        "tender_title": tender_title,
        "tender_reference": tender_reference,
        "tender_type": tender_type,
    }

    if not pricing_requirements:
        instructions = (
            "No structured pricing_requirements were provided to the "
            "tri-tender-pricing-mcp.\n\n"
            "Next steps for the client LLM (Tri-Tender Orchestrator):\n"
            "1) Ask the user to upload the pricing schedule / Bill of "
            "   Quantities (BOQ) or any annexure that contains the "
            "   rates, quantities and units to be priced.\n"
            "2) Use the 'tender-docs-mcp-file-resource' MCP to parse the "
            "   uploaded pricing document and extract line items into a "
            "   structured list.\n"
            "   Example (pseudo-call):\n"
            "     tender-docs-mcp-file-resource__extract_pricing_requirements(\n"
            "         file=uploaded_pricing_file\n"
            "     )\n"
            "3) Call pricing_entrypoint AGAIN, this time passing the "
            "   extracted pricing_requirements list into this tool.\n"
        )

        return {
            "status": "missing_pricing_spec",
            "needs_pricing_spec": True,
            "instructions_for_client_llm": instructions,
            "tender_context": tender_context,
        }

    pricing_analysis = None
    if parsed_pricing_spec_text:
        pricing_analysis = analyze_pricing_spec_text(
            parsed_pricing_spec_text,
            tender_type=tender_type,
        )

    return {
        "status": "ready_for_pricing_model",
        "needs_pricing_spec": False,
        "instructions_for_client_llm": (
            "You may now call `build_pricing_model` on tri-tender-pricing-mcp "
            "to generate a detailed pricing table, followed by "
            "`generate_pricing_report_html` to produce the final styled HTML "
            "pricing report. You may also call `compare_pricing_scenarios` "
            "to run low/balanced/premium what-if comparisons."
        ),
        "tender_context": tender_context,
        "pricing_requirements": pricing_requirements,
        "pricing_analysis": pricing_analysis,
    }


@mcp.tool
def build_pricing_model(
    pricing_items: List[Dict[str, Any]],
    strategy: Literal["low_cost", "balanced", "premium"] = "balanced",
    overhead_pct: float = 15.0,
    profit_margin_pct: float = 20.0,
    contingency_pct: float = 5.0,
    tax_rate_pct: float = 15.0,
    currency_symbol: str = "R",
) -> Dict[str, Any]:
    """
    Build a high-level pricing model from structured pricing items.

    Applies overheads, profit, contingency and tax. All calculations are
    returned so the client LLM can explain or adjust them with the user.
    """
    typed_items: List[PricingItemInput] = [
        PricingItemInput(**item) for item in pricing_items
    ]

    pricing_table = build_pricing_table(
        typed_items=typed_items,
        strategy=strategy,
        overhead_pct=overhead_pct,
        profit_margin_pct=profit_margin_pct,
        contingency_pct=contingency_pct,
        tax_rate_pct=tax_rate_pct,
        currency_symbol=currency_symbol,
    )

    return pricing_table


@mcp.tool
def compare_pricing_scenarios(
    pricing_items: List[Dict[str, Any]],
    strategies: Optional[List[Literal["low_cost", "balanced", "premium"]]] = None,
    overhead_pct: float = 15.0,
    profit_margin_pct: float = 20.0,
    contingency_pct: float = 5.0,
    tax_rate_pct: float = 15.0,
    currency_symbol: str = "R",
) -> Dict[str, Any]:
    """
    Run side-by-side "what-if" pricing scenarios (low/balanced/premium).

    This tool uses the same engine as build_pricing_model but calculates
    multiple strategies in one call so that the user can see how pricing
    posture affects totals and risk.
    """
    if strategies is None or len(strategies) == 0:
        strategies = ["low_cost", "balanced", "premium"]

    typed_items: List[PricingItemInput] = [
        PricingItemInput(**item) for item in pricing_items
    ]

    scenarios: Dict[str, Any] = {}
    comparison_list: List[Dict[str, Any]] = []

    for strat in strategies:
        model = build_pricing_table(
            typed_items=typed_items,
            strategy=strat,
            overhead_pct=overhead_pct,
            profit_margin_pct=profit_margin_pct,
            contingency_pct=contingency_pct,
            tax_rate_pct=tax_rate_pct,
            currency_symbol=currency_symbol,
        )
        scenarios[strat] = model

        totals = model.get("totals", {})
        comparison_list.append({
            "strategy": strat,
            "total_excl_tax": totals.get("total_excl_tax", 0.0),
            "total_incl_tax": totals.get("total_incl_tax", 0.0),
            "profit_amount": totals.get("profit_amount", 0.0),
            "overhead_amount": totals.get("overhead_amount", 0.0),
            "contingency_amount": totals.get("contingency_amount", 0.0),
        })

    return {
        "scenarios": scenarios,
        "comparison": {
            "currency_symbol": currency_symbol,
            "by_strategy": comparison_list,
        },
    }


@mcp.tool
def generate_pricing_report_html(
    tender_context: Dict[str, Any],
    company_context: Dict[str, Any],
    pricing_model: Dict[str, Any],
    additional_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Render a styled HTML pricing report suitable for PDF conversion.
    """
    html = render_pricing_report_html(
        tender_context=tender_context,
        company_context=company_context,
        pricing_model=pricing_model,
        additional_notes=additional_notes,
    )

    from datetime import datetime, timezone

    metadata = {
        "tender_context": tender_context,
        "company_context": company_context,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "html": html,
        "metadata": metadata,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
