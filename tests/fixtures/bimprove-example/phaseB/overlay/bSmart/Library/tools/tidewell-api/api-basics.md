# Tidewell API basics

- Base URL: `https://api.tidewell.example/v2`; times are UTC.
- Auth: `X-Tide-Key` header.
- Rate limit: 120 requests per minute per key; HTTP 429 with `Retry-After` when over.
- Paging: 50 items per page; pass the `after` cursor for the next page.
- Endpoints: `/tides`, `/stations`, `/berths`, `/vessels`.

Source: sources/tidewell-api-guide.md
Date: 2026-11-20
