# Footer statistics

Hugo renders the counters and SVG paths into every page. Country counts appear
in map hover titles; no country-name/count list is displayed. The footer
requires no JavaScript or external requests to display. Tracking new activity
still requires GoatCounter to be reachable and allowed by the visitor's browser.
The footer displays the snapshot date. GitHub Actions schedules a refresh every
15 minutes, at minutes 7, 22, 37 and 52 of each hour (UTC). Scheduling and deployment
can add a delay. Reload the page after the deployment to see the new snapshot.
The page does not poll or update an already-open tab automatically.

The refresh workflow uses the GoatCounter API (`https://www.goatcounter.com/api.json`),
including pagination for both hits and locations. The locations request includes
only page path IDs, excluding download and click-through events. It validates
responses and replaces `data/livestats.json` atomically. Failed requests preserve the previous
snapshot and its timestamp. Actions caches the last successful snapshot between
runs; the committed JSON is the fallback if the cache is unavailable.

Set the repository Actions secret `GOATCOUNTER_TOKEN` to a read-only statistics
API token. The refresh script prefers this secret; the existing TOML token is a
compatibility fallback. Once the secret is configured, remove the TOML token and
revoke/replace that old token because it has been committed to Git history.
Never pass an API token into a template or client-side JavaScript.

The first three counters include only the 2026 report edition (draft and final
filenames); 2025 reports are excluded. The first five counters sum named events
in `layouts/partials/visitor-stats.html`. Each new download or Zenodo click is sent
with GoatCounter's `no_session` option, so repeated clicks are counted separately.
`static/js/activity.js` queues clicks in memory while the tracker loads and owns
event binding to avoid duplicate tracking. It respects the tracker's normal
browser exclusions. Historical events used session deduplication; unrecorded
repeat clicks cannot be reconstructed from the aggregate snapshot.
These are recorded click counts, not independently verified file transfers.
Tracking semantics: https://www.goatcounter.com/help/js and
https://www.goatcounter.com/help/events.

The sixth counter, Website visits, sums the recorded page visits across all page
paths (paths starting with `/`); event names cannot start with `/`. It retains
GoatCounter's default session deduplication per page, and is not a count of unique
people across the whole website. It uses the same date window as the map.
Taiwan location rows are aggregated into China for this site's reporting. The
China SVG feature includes the Taiwan geometry, with one shared count and hover
title; aliases also handle older snapshots with separate Taiwan rows.

A zero means no activity was recorded for that counter in the snapshot.
An unavailable snapshot displays a dash, not zero. Download event names must stay
in sync with the download links and table CSV handler.

The country geometry in `data/visitor_map.json` was projected once from
world-atlas 2.0.2 countries-110m using D3 7.9.0 Natural Earth 1 and topojson-client
3.1.0, excluding Antarctica. Coordinates use a 640 × 320 viewBox and two decimal
places. Geography is bundled with the site; no map/CDN request runs in the browser.
Tiny countries may not exist at this scale; the aggregate snapshot retains all records.
Geometry source: https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json
Natural Earth source data: https://www.naturalearthdata.com/about/terms-of-use/
See `world-atlas-LICENSE.txt` for the redistribution license.

Checks:

```sh
python3 -m unittest discover -s tests -v  # Python 3.11+
node --test tests/test_activity.js
hugo --minify
```

Review the generated page with JavaScript disabled and third-party requests
blocked, at desktop and mobile widths. `#visitor-map` should contain 175 paths;
United Kingdom and Greece should show the counts in the current snapshot.
