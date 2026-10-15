# Footer statistics

Hugo renders the counters, country list and SVG paths into every page. The footer
requires no JavaScript or external requests to display. Tracking new activity
still requires GoatCounter to be reachable and allowed by the visitor's browser.
The footer displays the snapshot date. GitHub Actions schedules a refresh every
15 minutes, at minutes 7, 22, 37 and 52 of each hour (UTC). Scheduling and deployment
can add a delay. Reload the page after the deployment to see the new snapshot.
The page does not poll or update an already-open tab automatically.

The refresh workflow uses the GoatCounter API (`https://www.goatcounter.com/api.json`),
including pagination for both hits and locations. It validates both responses and
replaces `data/livestats.json` atomically. Failed requests preserve the previous
snapshot and its timestamp. Actions caches the last successful snapshot between
runs; the committed JSON is the fallback if the cache is unavailable.

Set the repository Actions secret `GOATCOUNTER_TOKEN` to a read-only statistics
API token. The refresh script prefers this secret; the existing TOML token is a
compatibility fallback. Once the secret is configured, remove the TOML token and
revoke/replace that old token because it has been committed to Git history.
Never pass an API token into a template or client-side JavaScript.

The first three counters include only the 2026 report edition (draft and final
filenames); 2025 reports are excluded. The five counters sum the named events in `layouts/partials/visitor-stats.html`.
They reflect GoatCounter's recorded visitor/event counts, not independently
verified file transfers. A zero means no event was recorded in the snapshot.
An unavailable snapshot displays a dash, not zero. Download event names must stay
in sync with the download links and table CSV handler.

The country geometry in `data/visitor_map.json` was projected once from
world-atlas 2.0.2 countries-110m using D3 7.9.0 Natural Earth 1 and topojson-client
3.1.0, excluding Antarctica. Coordinates use a 640 × 320 viewBox and two decimal
places. Geography is bundled with the site; no map/CDN request runs in the browser.
Tiny countries may not exist at this scale; the country list retains all records.
Geometry source: https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json
Natural Earth source data: https://www.naturalearthdata.com/about/terms-of-use/
See `world-atlas-LICENSE.txt` for the redistribution license.

Checks:

```sh
python3 -m unittest discover -s tests -v  # Python 3.11+
hugo --minify
```

Review the generated page with JavaScript disabled and third-party requests
blocked, at desktop and mobile widths. `#visitor-map` should contain 176 paths;
United Kingdom and Greece should show the counts in the current snapshot.
