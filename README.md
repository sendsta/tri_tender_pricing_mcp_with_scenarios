
# Tri-Tender Pricing MCP (FastMCP-compatible)

This is the Tri-Tender **public & private tender pricing MCP**, implemented
with the core `fastmcp` server so that it runs cleanly on **FastMCP Cloud**.

## Server object

FastMCP Cloud will look for a `FastMCP` instance named **`mcp`**:

```python
from fastmcp import FastMCP

mcp = FastMCP(name="tri-tender-pricing-mcp")
```

## Tools

- `pricing_entrypoint`
- `build_pricing_model`
- `compare_pricing_scenarios`
- `generate_pricing_report_html`

## Local run

```bash
pip install -r requirements.txt
python server.py
```

## FastMCP Cloud

In FastMCP Cloud, set the **Entrypoint** to:

```text
server.py:mcp
```

Python version: **3.12**
