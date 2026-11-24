# Tidewell API guide (v2)

Tidewell is a public API for harbour and tide data.

- Base URL: `https://api.tidewell.example/v2`
- Authentication: send your key in the `X-Tide-Key` header.
- Rate limit: 120 requests per minute per key. Over the limit you get HTTP 429
  with a `Retry-After` header.
- Paging: list endpoints return 50 items. Pass the `after` cursor from the last
  response to get the next page.
- Endpoints: `/tides`, `/stations`, `/berths`, `/vessels`.
- All times are UTC, ISO 8601.
