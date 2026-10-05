"""Load the Google Form CSV export into PrepMap.

Usage: python import_form.py responses.csv

Rename the form's columns (or edit COLUMNS below) so they match.
"""
import csv
import sys

import db
from extract import from_form_row, pick_route

# form column header -> our field
COLUMNS = {
    "Company": "company",
    "Role": "role",
    "Year": "year",
    "Outcome": "outcome",
    "How you got in": "route",
    "Rounds": "rounds",
    "Topics": "topics",
    "Days between rounds": "timeline",
    "Resources": "resources",
    "Mistake": "mistake",
    "What I wish I knew": "advice",
    "Proof link": "proof_url",
    "Summary consent": "consent_summary",
    "Contact consent": "consent_contact",
    "Name": "name",
    "Contact": "contact",
}


def outcome(v):
    v = (v or "").lower()
    if "offer" in v:
        return "offer"
    if "reject" in v:
        return "rejected"
    if "no" in v:
        return "no reply"
    return "unknown"


def yes(v):
    return 1 if (v or "").strip().lower().startswith("y") else 0


def main(path):
    db.init()
    added = skipped = 0
    with open(path, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row = {ours: (raw.get(theirs) or "").strip() for theirs, ours in COLUMNS.items()}
            if not row["company"] or not yes(row["consent_summary"]):
                skipped += 1
                continue
            story = {
                "company": row["company"],
                "role": row["role"] or None,
                "year": int(row["year"]) if row["year"].isdigit() else None,
                "outcome": outcome(row["outcome"]),
                "route": pick_route(row["route"]),
                "source": "form",
                "raw_text": None,
                "name": row["name"] or None,
                "contact": row["contact"] or None,
                "proof_url": row["proof_url"] or None,
                "consent_summary": 1,
                "consent_contact": yes(row["consent_contact"]),
                "approved": 1,
            }
            db.save_story(story, from_form_row(row))
            added += 1
    print(f"added {added}, skipped {skipped} (no company or no consent)")


if __name__ == "__main__":
    main(sys.argv[1])
