# harbor-app sync meeting, 2026-11-12

Present: product owner, two developers, Gullwing Marine (client).

- harbor-app reads berth occupancy from Tidewell's `/berths` endpoint only.
  `/vessels` is out of scope for now.
- Gullwing Marine wants one full sync every day at 02:00 local time, when the
  harbour is quiet.
- Keep the last 30 days of berth history in harbor-app.
- Open: whether to add an hourly delta sync later.
- Lunch was fine. Next meeting in two weeks.
