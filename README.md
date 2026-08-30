# google-ads-kw-mcp

MCP server that exposes Google Ads keyword search volumes to AI agents — a
**free** alternative to paid keyword-volume APIs, using the same
`KeywordPlanIdeaService` that powers Google's Keyword Planner.

## Why this instead of the official Google Ads MCP?

The official Google Ads MCP talks GAQL/REST and can't query
`KeywordPlanIdeaService`. This server is complementary, not a duplicate —
use it specifically for search volume, and the official one (or
[google-ads-write-mcp](../google-ads-write-mcp)) for everything else.

## Tools (2)

### `get_keyword_volumes`

Returns search volume data for an array of keywords.

| Param | Type | Default | Description |
|---|---|---|---|
| `keywords` | `list[str]` | required | Max 20 keywords per call |
| `customer_id` | `str` | required | Google Ads account ID (no dashes) |
| `country` | `str` | `"ES"` | ISO country code (see `list_keyword_countries`) |
| `language` | `str` | `"es"` | Language code (es, en, fr, de, it, pt, nl, ja, zh, ru, ar) |

Response:
```json
[
  {
    "keyword": "surf lessons",
    "avg_monthly_searches": 480,
    "competition": "MEDIUM",
    "competition_index": 38,
    "low_top_of_page_bid_micros": 206702,
    "high_top_of_page_bid_micros": 980973
  }
]
```

### `list_keyword_countries`

Returns the 20 supported countries (ISO code → name).

## Security

- The tool ships with [MCP Tool Annotations](https://modelcontextprotocol.io/specification)
  (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) — this server is read-only,
  so both tools are annotated accordingly, letting MCP clients skip any confirmation prompt.
- Execution errors propagate as real MCP protocol errors (`isError: true`), not as a JSON payload
  that looks like a success with an `"error"` key buried inside — so the calling model actually
  sees the failure and can self-correct instead of silently treating it as a success.

## Setup

You need a Google Ads **developer token** (Standard Access is enough) and an
OAuth client authorized against your Google Ads MCC/account. If you already
have a `google-ads.yaml` from the Google Ads API client library, you can
adapt its `client_id`/`client_secret`/`refresh_token` into the JSON format
below.

1. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Create `~/.config/google-ads-mcp/credentials.json`:
   ```json
   {
     "client_id": "...",
     "client_secret": "...",
     "refresh_token": "..."
   }
   ```

## MCP client configuration

```json
{
  "mcpServers": {
    "google-ads-kw": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/google-ads-kw-mcp/server.py"],
      "env": {
        "GOOGLE_ADS_CREDENTIALS_PATH": "~/.config/google-ads-mcp/credentials.json",
        "GOOGLE_ADS_DEVELOPER_TOKEN": "<your developer token>",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "<your MCC customer id, no dashes>"
      }
    }
  }
}
```

| Env var | Purpose |
|---|---|
| `GOOGLE_ADS_CREDENTIALS_PATH` | Path to the credentials JSON (default: `~/.config/google-ads-mcp/credentials.json`) |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Your Google Ads developer token |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Your MCC/login customer ID, no dashes |
| `GOOGLE_ADS_API_VERSION` | Google Ads API version (default: `v25`, pinned in `server.py`). This is deliberately fixed rather than inheriting the `google-ads` library's default, so a `pip install --upgrade google-ads` can't silently move you to a newer API version. Only override after reading the [release notes](https://developers.google.com/google-ads/api/docs/release-notes). |

## Limits

- Max 20 keywords per call (API limit).
- Long-tail keywords may return `avg_monthly_searches: 0` if Google Ads
  doesn't have enough data.
- Free quota is generous (~15,000 ops/day for standard accounts) — plenty
  for this use case.

## License

MIT — see [LICENSE](LICENSE).
