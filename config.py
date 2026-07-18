"""
Watchlist configuration for FEC + CalAccess monitoring.

INDIVIDUALS: each entry has a canonical display name and a list of
(last, first) name variants to match against, since campaign finance
systems record names as "Last, First" and people use nicknames /
formal names inconsistently across filings.

COMMITTEES: names of PACs / organizations to track filings for.
FEC_COMMITTEE_IDS can be filled in once you resolve them (see
fec_watcher.resolve_committee_ids()) to avoid re-searching by name
every run.
"""

INDIVIDUALS = [
    {"display": "Chris (Christian) Larsen", "variants": [("Larsen", "Chris"), ("Larsen", "Christian")]},
    {"display": "Michael Moritz", "variants": [("Moritz", "Michael")]},
    {"display": "Sergey Brin", "variants": [("Brin", "Sergey")]},
    {"display": "Ben Horowitz", "variants": [("Horowitz", "Ben"), ("Horowitz", "Benjamin")]},
    {"display": "Marc Andreessen", "variants": [("Andreessen", "Marc")]},
    {"display": "Anna Brockman", "variants": [("Brockman", "Anna")]},
    {"display": "Greg Brockman", "variants": [("Brockman", "Greg"), ("Brockman", "Gregory")]},
    {"display": "John Doerr III", "variants": [("Doerr", "John")]},
    {"display": "Dario Amodei", "variants": [("Amodei", "Dario")]},
    {"display": "Sam (Samuel) Altman", "variants": [("Altman", "Sam"), ("Altman", "Samuel")]},
    {"display": "Reed Hastings", "variants": [("Hastings", "Reed"), ("Hastings", "Wilmot")]},
    {"display": "Patrick Collison", "variants": [("Collison", "Patrick")]},
    {"display": "Tim Draper", "variants": [("Draper", "Tim"), ("Draper", "Timothy")]},
    {"display": "Peter Thiel", "variants": [("Thiel", "Peter")]},
    {"display": "Eric Schmidt", "variants": [("Schmidt", "Eric")]},
    {"display": "Ron Conway", "variants": [("Conway", "Ron"), ("Conway", "Ronald")]},
    {"display": "Tony Xu", "variants": [("Xu", "Tony")]},
    {"display": "Steve Jurvetson", "variants": [("Jurvetson", "Steve"), ("Jurvetson", "Steven")]},
    {"display": "Joe Lonsdale", "variants": [("Lonsdale", "Joe"), ("Lonsdale", "Joseph")]},
    {"display": "Garry Tan", "variants": [("Tan", "Garry")]},
    {"display": "Brian Singerman", "variants": [("Singerman", "Brian")]},
    # "David Crane" is a common name -- FEC/CalAccess results should be
    # sanity-checked against employer/occupation fields to avoid false positives.
    {"display": "David Crane", "variants": [("Crane", "David")]},
    {"display": "Neil Mehta", "variants": [("Mehta", "Neil")]},
]

COMMITTEES = [
    "Golden State Promise",
    "Govern for California",
    "Building Back a Better California",
    "California Back to Basics",
    "California Business Roundtable",
    "California Chamber of Commerce",
]

# Optional: once you know a committee's FEC committee ID (e.g. "C00123456"),
# put it here so fec_watcher can query /filings directly instead of
# re-searching by name every run. Most of the committees above are
# CA state-level PACs and likely have no FEC ID at all -- that's fine,
# the watcher just won't find matches on the FEC side for those.
FEC_COMMITTEE_IDS = {
    # "Golden State Promise": "C00XXXXXX",
}

# Where local state (seen-item IDs, generated feed) lives.
STATE_DIR = "state"
SEEN_STORE_PATH = f"{STATE_DIR}/seen.json"
FEED_PATH = f"{STATE_DIR}/feed.xml"

# Feed metadata
FEED_TITLE = "Campaign Finance Watch — FEC & CalAccess"
FEED_DESCRIPTION = "Alerts for donations and filings involving a tracked watchlist of individuals and committees."
FEED_LINK = "https://example.com/campaign-watch"  # replace with wherever you host feed.xml
