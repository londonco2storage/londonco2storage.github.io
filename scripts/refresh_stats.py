#!/usr/bin/env python3
"""Refresh the public aggregate snapshot. Requires Python 3.11+; no dependencies."""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib
from urllib.parse import urlencode
from urllib.request import Request, urlopen

START = "2025-01-01"


def get_json(site, token, endpoint, params):
    query = urlencode(params)
    request = Request(
        f"https://{site}.goatcounter.com/api/v0/stats/{endpoint}?{query}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def page_rows(payload, key):
    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
        raise ValueError(f"Invalid {key} response")
    if type(payload.get("more")) is not bool:
        raise ValueError("Missing pagination status")
    for row in payload[key]:
        if not isinstance(row, dict) or type(row.get("count")) is not int or row["count"] < 0:
            raise ValueError("Invalid aggregate count")
    if payload["more"] and not payload[key]:
        raise ValueError("Pagination made no progress")
    return payload[key], payload["more"]


def collect(fetch, endpoint, key, name_key, params, page_ids=None):
    totals = defaultdict(int)
    seen = set()
    excluded = []
    offset = 0
    for _ in range(100):
        query = dict(params, limit=100)
        if endpoint == "hits" and excluded:
            query["exclude_paths"] = ",".join(map(str, excluded))
        elif endpoint == "locations":
            query["offset"] = offset
        rows, more = page_rows(fetch(endpoint, query), key)
        for row in rows:
            name = row.get(name_key)
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Missing aggregate name")
            identifier = row.get("path_id" if endpoint == "hits" else "id")
            if not identifier or identifier in seen:
                raise ValueError("Missing or repeated pagination ID")
            seen.add(identifier)
            if endpoint == "hits":
                if type(row.get("event")) is not bool:
                    raise ValueError("Missing event classification")
                excluded.append(identifier)
                if page_ids is not None and not row["event"]:
                    page_ids.append(identifier)
            elif identifier == "TW" or name in ("Taiwan", "Taiwan, Province of China", "Taiwan (Province of China)", "Taiwan, China"):
                # Site reporting convention: include these visits in China.
                name = "China"
            totals[name] += row["count"]
        if not more:
            return [{name_key: name, "count": count} for name, count in
                    sorted(totals.items(), key=lambda item: (-item[1], item[0]))]
        offset += len(rows)
    raise ValueError("Pagination limit exceeded")


def refresh(output, fetch, now):
    # Use one date window for both requests. Never publish a partial snapshot.
    end = (now.date() + timedelta(days=1)).isoformat()
    params = {"start": START, "end": end}
    page_ids = []
    hits = collect(fetch, "hits", "hits", "path", params, page_ids)
    # Restrict geography to page visits. Download/link events must not inflate it.
    countries = collect(fetch, "locations", "stats", "name",
                        dict(params, include_paths=",".join(map(str, page_ids)))) if page_ids else []
    snapshot = {
        "generated": now.strftime("%Y-%m-%d %H:%M UTC"),
        "start": START,
        "end": end,
        "hits": hits,
        "countries": countries,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(snapshot, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        temporary.replace(output)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/livestats.json")
    parser.add_argument("--config", default="data/register.toml")
    args = parser.parse_args()
    updated = False
    try:
        with open(args.config, "rb") as stream:
            meta = tomllib.load(stream).get("meta", {})
        site = os.environ.get("GOATCOUNTER_SITE") or meta.get("goatcounter", "")
        # Keep existing deployments working while moving the credential to Secrets.
        token = os.environ.get("GOATCOUNTER_TOKEN") or meta.get("goatcounter_token", "")
        if not re.fullmatch(r"[a-zA-Z0-9-]+", site) or not token:
            raise ValueError("Missing statistics configuration")
        snapshot = refresh(args.output, lambda endpoint, params: get_json(site, token, endpoint, params),
                           datetime.now(timezone.utc))
        updated = True
        print(f"Statistics updated: {len(snapshot['hits'])} paths, {len(snapshot['countries'])} countries.")
    except Exception as error:
        # Do not log response bodies, URLs with credentials, or replace valid data with zeroes.
        print(f"::warning::Statistics refresh failed ({type(error).__name__}); keeping the previous snapshot.")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            stream.write(f"updated={str(updated).lower()}\n")


if __name__ == "__main__":
    main()
