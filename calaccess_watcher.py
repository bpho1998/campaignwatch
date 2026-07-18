"""
CalAccess watcher.

IMPORTANT CAVEAT: unlike the FEC, California's CAL-ACCESS system has no
live API. The Secretary of State only publishes a bulk relational-database
export, refreshed roughly once a day:
    https://cal-access.sos.ca.gov/campaign/  (see "Raw Data" link)
    (also mirrored/cleaned nightly by the California Civic Data Coalition:
     https://calaccess.californiacivicdata.org/downloads/latest/)

So the CalAccess side of this can realistically only be "checked once a
day" -- there is no way to get second-by-second alerts out of the state's
own data. This script downloads that daily export, extracts two tables,
and diffs against what it saw last time:

  - RCPT_CD          itemized contributions received (donations), with
                      contributor name in CTRIB_NAML / CTRIB_NAMF
  - CVR_CAMPAIGN_DISCLOSURE_CD + FILER_FILINGS_CD
                      cover-page / filing metadata, used to catch new
                      filings by the tracked committees (by filer name)

CAL-ACCESS's schema has shifted before and will shift again once the
CARS replacement system (targeted Nov 2026) goes live -- check
https://www.sos.ca.gov/campaign-lobbying/cal-access-resources/cal-access-data-columns
before relying on the column names below, and adjust as needed.
"""
import csv
import io
import os
import zipfile

import requests

import config
from feed_store import WatchItem

BULK_DATA_URL = "https://campaignfinance.cdn.sos.ca.gov/dbwebexport.zip"
DOWNLOAD_CACHE = "state/dbwebexport.zip"


def _download_bulk_export() -> str:
    os.makedirs("state", exist_ok=True)
    resp = requests.get(BULK_DATA_URL, timeout=300, stream=True)
    resp.raise_for_status()
    with open(DOWNLOAD_CACHE, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    return DOWNLOAD_CACHE


def _read_table(zf: zipfile.ZipFile, table_filename: str):
    """CAL-ACCESS exports are pipe- or tab-delimited .TSV files inside the
    zip, one per table. Filenames are case-insensitive matches to table
    names, e.g. RCPT_CD.TSV. Adjust delimiter/encoding if a given export
    differs."""
    matches = [n for n in zf.namelist() if n.upper().endswith(table_filename.upper())]
    if not matches:
        return
    with zf.open(matches[0]) as f:
        text = io.TextIOWrapper(f, encoding="latin-1")
        reader = csv.DictReader(text, delimiter="\t")
        for row in reader:
            yield row


def _name_matches(last: str, first: str, naml: str, namf: str) -> bool:
    if not naml:
        return False
    naml = naml.strip().upper()
    namf = (namf or "").strip().upper()
    return last.upper() == naml and (not namf or first.upper() in namf or namf in first.upper())


def check_contributions(seen: set, zip_path: str) -> list:
    items = []
    with zipfile.ZipFile(zip_path) as zf:
        for row in _read_table(zf, "RCPT_CD.TSV"):
            naml = row.get("CTRIB_NAML", "")
            namf = row.get("CTRIB_NAMF", "")
            for person in config.INDIVIDUALS:
                if any(_name_matches(last, first, naml, namf) for last, first in person["variants"]):
                    rid = f"{row.get('FILING_ID')}-{row.get('LINE_ITEM')}"
                    if rid in seen:
                        continue
                    amount = row.get("AMOUNT", "0")
                    recipient = row.get("FILER_NAML", "unknown recipient")
                    date = row.get("RCPT_DATE", "")
                    items.append(WatchItem(
                        id=f"ca-rcpt-{rid}",
                        title=f"CalAccess: {person['display']} donated ${amount} to {recipient}",
                        link=f"https://cal-access.sos.ca.gov/Campaign/Committees/Detail.aspx?id={row.get('FILER_ID', '')}",
                        description=f"{naml}, {namf} gave ${amount} to {recipient} on {date} (filing {row.get('FILING_ID')}).",
                    ))
                    seen.add(rid)
                    break
    return items


def check_committee_filings(seen: set, zip_path: str) -> list:
    items = []
    with zipfile.ZipFile(zip_path) as zf:
        for row in _read_table(zf, "CVR_CAMPAIGN_DISCLOSURE_CD.TSV"):
            filer_name = (row.get("FILER_NAML") or "").upper()
            for committee in config.COMMITTEES:
                if committee.upper() in filer_name:
                    fid = str(row.get("FILING_ID"))
                    if not fid or fid in seen:
                        continue
                    form = row.get("FORM_TYPE", "")
                    date = row.get("RPT_DATE", "")
                    items.append(WatchItem(
                        id=f"ca-filing-{fid}",
                        title=f"CalAccess: {committee} filed {form}",
                        link=f"https://cal-access.sos.ca.gov/Campaign/Committees/Detail.aspx?id={row.get('FILER_ID','')}",
                        description=f"{row.get('FILER_NAML')} filed form {form} on {date} (filing {fid}).",
                    ))
                    seen.add(fid)
                    break
    return items


def run(seen: set) -> list:
    zip_path = _download_bulk_export()
    items = []
    items += check_contributions(seen, zip_path)
    items += check_committee_filings(seen, zip_path)
    os.remove(zip_path)
    return items


if __name__ == "__main__":
    seen = set()
    for item in run(seen):
        print(item.title)
