# Campaign Finance Watch

Monitors a watchlist of individuals and committees for new **FEC** donations/filings
and **CalAccess** (California) donations/filings, and publishes matches as an RSS feed
(`state/feed.xml`) that any feed reader can subscribe to.

## Speed, honestly

- **FEC**: near real-time. New electronic filings post within minutes of being
  submitted, and this polls the official API. Run it every 5 minutes and you'll
  hear about things minutes after they're filed.
- **CalAccess**: capped at ~once a day. California's Secretary of State only
  publishes a full bulk data export, refreshed roughly daily — there's no live
  API to poll faster than that, regardless of what this script does. (A
  replacement system, CARS, is targeted to launch November 2026 and may offer
  better access — worth revisiting then.)

An RSS reader itself also polls on its own schedule (typically 15–60 min), so
"instant" here really means: FEC items usually show up in your reader within
~20 minutes of being filed; CalAccess items show up within a day.

## Setup

```bash
pip install -r requirements.txt
```

Get a free FEC API key at https://api.data.gov/signup/ (the `DEMO_KEY` default
works but is capped at ~30 requests/hour, too low for a real polling loop).

```bash
export FEC_API_KEY=your_key_here
```

## Editing the watchlist

Open `config.py` — `INDIVIDUALS` and `COMMITTEES` are already populated with
the names you gave me. To reduce false positives on common names (e.g. "David
Crane"), cross-check hits against the employer/occupation fields included in
each alert's description before trusting them.

Committees are matched by name on both sides. Federal committee IDs (needed
for the FEC `/filings` check) aren't auto-resolved — run:

```bash
python3 fec_watcher.py
```

This prints any FEC committee IDs it can find for your watchlist committee
names. Most of the six committees you listed are California *state* PACs, so
they may return nothing on the FEC side — that's expected, not a bug. Paste
any matches you want tracked into `config.FEC_COMMITTEE_IDS`.

## Running it

```bash
python3 run_watch.py                 # both FEC + CalAccess
python3 run_watch.py --fec-only      # just the fast-moving side
python3 run_watch.py --calaccess-only
```

Each run updates `state/seen.json` (dedupe store) and rewrites
`state/feed.xml` (RSS output), prepending new items to the existing feed
history.

## Scheduling

Cron example — FEC checked every 5 minutes, CalAccess once a day:

```cron
*/5 * * * *  cd /path/to/campaign-watch && FEC_API_KEY=xxx python3 run_watch.py --fec-only  >> log.txt 2>&1
0   7 * * *  cd /path/to/campaign-watch && python3 run_watch.py --calaccess-only            >> log.txt 2>&1
```

## Making the feed subscribable

`state/feed.xml` needs to live somewhere with a stable public URL for a feed
reader to poll. Options, roughly easiest first:

1. **GitHub Pages / a public GitHub repo**: commit `state/feed.xml` on every
   run (add a `git add/commit/push` step after `run_watch.py` in your cron
   job) and point a feed reader at the raw file URL or the Pages URL.
2. **A cheap always-on VPS**: run this via cron and serve `state/` with
   nginx/Caddy, or just `python3 -m http.server` inside a systemd service.
3. **S3 / Cloudflare R2 + static hosting**: upload `feed.xml` after each run;
   both support plain public URLs without needing a server.
4. **GitHub Actions on a schedule**: run `run_watch.py` in a scheduled
   Action, commit the updated `feed.xml` back to the repo. No server to
   maintain at all — probably the lowest-effort option if you're already
   comfortable with GitHub.

Once it's at a public URL, add that URL to Feedly, NetNewsWire, an RSS-to-Slack
bridge, or anything else that reads RSS.

## Notes / things worth double-checking before relying on this

- CalAccess's bulk-export column names (`CTRIB_NAML`, `RCPT_CD`, etc.) are
  based on the documented schema but CAL-ACCESS has changed its layout before.
  If `calaccess_watcher.py` starts returning nothing, check
  https://www.sos.ca.gov/campaign-lobbying/cal-access-resources/cal-access-data-columns
  for current table/column names.
- The FEC `schedule_a` matching is name-based (`"Larsen, Chris"` etc.), same
  as the underlying data — it will occasionally need widening (or narrowing,
  for common names) as you see real results.
- Consider adding a second alert channel (email/Slack webhook) directly inside
  `run_watch.py` alongside the RSS write if you don't want to depend on your
  feed reader's own polling delay for the FEC side.
