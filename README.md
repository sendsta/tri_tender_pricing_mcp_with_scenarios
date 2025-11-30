
# Tri-Tender Pricing MCP (HTTP / FastMCP Cloud Ready)

This is the Tri-Tender public & private **pricing MCP**, implemented using
the core `fastmcp` server with HTTP transport so it runs cleanly on
**FastMCP Cloud**.

## Tools

- `pricing_entrypoint`
- `build_pricing_model`
- `compare_pricing_scenarios`
- `generate_pricing_report_html`

## Running locally

```bash
pip install -r requirements.txt
python server.py
```

The MCP endpoint will be available at:

- `http://localhost:8080/mcp` (by default) or
- `http://localhost:<PORT>/mcp` if you set `PORT` env var.

## FastMCP Cloud

On FastMCP Cloud:

- Entrypoint: `server.py`
- Python: 3.12
- `fastmcp` will be detected automatically and `fastmcp inspect` works
  out of the box.
