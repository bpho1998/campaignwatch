"""
FEC watcher.

Uses the official FEC API (https://api.open.fec.gov/v1). Get a free key at
https://api.data.gov/signup/ and set it as the FEC_API_KEY environment
variable. The demo key ("DEMO_KEY") works but is rate-limited to ~30
requests/hour/IP -- fine for testing, not for a real polling loop.

Two things get checked:
  1. schedule_a -- itemized contributions ("donations") where the
     contributor name matches someone on the watchlist.
  2. filings -- new reports/filings for any watchlist committee that
     has a known FEC committee ID (see config.FEC_COMMITTEE_IDS).

Docs: https://api.open.fec.gov/developers/
"""
import os
import time
import requests

import config
from feed_store import WatchItem

BASE = "https://api.open.fec.gov/v1"
API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")

SESSION = requests.Session()
SESSION.params = {"api_key": API_KEY}


def _get(path: str, **params) -> dict:
    resp = SESSION.get(f"{BASE}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def resolve_committee_ids() -> dict:
    """Best-effort lookup of FEC committee IDs by name for watchlist
    committees. Run this once and paste results into
    config.FEC_COMMITTEE_IDS -- many of these are CA state PACs and
    will simply return no FEC match, which is expected."""
    found = {}
    for name in config.COMMITTEES:
        try:
            data = _get("/committees/", q=name, per_page=5)
        except requests.HTTPError:
            continue
        for res in data.get("results", []):
            found.setdefault(name, []).append(
                (res.get("committee_id"), res.get("name"))
            )
        time.sleep(0.3)
    return found


def check_contributions(seen: set) -> list:
    """Poll schedule_a for each individual on the watchlist."""
    items = []
    for person in config.INDIVIDUALS:
        for last, first in person["variants"]:
            contributor_name = f"{last}, {first}"
            try:
                data = _get(
                    "/schedule_a/",
                    contributor_name=contributor_name,
                    sort="-contribution_receipt_date",
                    per_page=20,
                    sort_hide_null=True,
                )
            except requests.HTTPError:
                continue

            for res in data.get("results", []):
                sub_id = str(res.get("sub_id"))
                if not sub_id or sub_id in seen:
                    continue
                amount = res.get("contribution_receipt_amount")
                recipient = (res.get("committee") or {}).get("name", "unknown recipient")
                date = res.get("contribution_receipt_date", "")
                items.append(WatchItem(
                    id=f"fec-sa-{sub_id}",
                    title=f"FEC: {person['display']} donated ${amount:,.0f} to {recipient}",
                    link=f"https://www.fec.gov/data/receipts/individual-contributions/?contributor_name={contributor_name.replace(' ', '+')}",
                    description=(
                        f"{res.get('contributor_name')} ({res.get('contributor_employer','')}, "
                        f"{res.get('contributor_occupation','')}) gave ${amount:,.2f} to {recipient} "
                        f"on {date}. Filed under image #{res.get('image_number')}."
                    ),
                ))
                seen.add(sub_id)
            time.sleep(0.3)
    return items


def check_committee_filings(seen: set) -> list:
    """Poll /filings for any watchlist committee with a known FEC ID."""
    items = []
    for name, cmte_id in config.FEC_COMMITTEE_IDS.items():
        try:
            data = _get(
                "/filings/",
                committee_id=cmte_id,
                sort="-receipt_date",
                per_page=10,
            )
        except requests.HTTPError:
            continue

        for res in data.get("results", []):
            fid = str(res.get("file_number") or res.get("sub_id"))
            if not fid or fid in seen:
                continue
            items.append(WatchItem(
                id=f"fec-filing-{fid}",
                title=f"FEC: {name} filed {res.get('form_type', 'a report')}",
                link=res.get("pdf_url") or f"https://www.fec.gov/data/committee/{cmte_id}/",
                description=f"{name} ({cmte_id}) filed {res.get('form_type')} on {res.get('receipt_date')}.",
            ))
            seen.add(fid)
        time.sleep(0.3)
    return items


def run(seen: set) -> list:
    items = []
    items += check_contributions(seen)
    items += check_committee_filings(seen)
    return items


if __name__ == "__main__":
    # Utility: run standalone to print resolvable FEC committee IDs
    # for the watchlist committees.
    for name, matches in resolve_committee_ids().items():
        print(name)
        for cid, cname in matches:
            print(f"   {cid}  {cname}")
