# harbor-app: Tidewell sync

- Reads berth occupancy from `/berths` only; `/vessels` is out of scope.
- Full sync once a day at 02:00 local time (client: Gullwing Marine).
- Keeps 30 days of berth history. Open: hourly delta sync later.
- General API facts: Library `tools/tidewell-api/api-basics.md`.

Source: sources/harbor-meeting-notes.md
Date: 2026-11-20
