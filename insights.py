"""Views across all stories: stats, explore, topics, compare, prep plans, single stories."""
import datetime
import math
from collections import defaultdict

import db
import plan
from extract import ROUND_TYPES


def _all():
    sts = db.stories()
    facts = db.facts_for([s["id"] for s in sts])
    return sts, facts


def stats():
    sts, facts = _all()
    companies = {s["company"].lower() for s in sts}
    return {
        "stories": len(sts),
        "companies": len(companies),
        "offers": sum(1 for s in sts if s["outcome"] == "offer"),
        "rejections": sum(1 for s in sts if s["outcome"] == "rejected"),
        "contactable": sum(1 for s in sts if s["consent_contact"]),
        "facts": len(facts),
    }


def explore(route=None, outcome=None):
    """One card per company or program, with the numbers a junior cares about."""
    sts, facts = _all()
    topics = defaultdict(set)
    for f in facts:
        if f["kind"] == "topic":
            topics[f["story_id"]].add(f["value"])

    cards = {}
    for s in sts:
        if route and s["route"] != route:
            continue
        if outcome and s["outcome"] != outcome:
            continue
        key = s["company"].lower()
        c = cards.setdefault(key, {"company": s["company"], "n": 0, "offers": 0, "rejected": 0,
                                   "years": set(), "routes": defaultdict(int),
                                   "topics": defaultdict(int), "contactable": 0})
        c["n"] += 1
        c["offers"] += s["outcome"] == "offer"
        c["rejected"] += s["outcome"] == "rejected"
        c["contactable"] += bool(s["consent_contact"])
        if s["year"]:
            c["years"].add(s["year"])
        c["routes"][s["route"] or "unknown"] += 1
        for t in topics[s["id"]]:
            c["topics"][t] += 1

    out = []
    for c in cards.values():
        c["top_topics"] = [t for t, _ in sorted(c["topics"].items(), key=lambda x: -x[1])[:3]]
        c["latest"] = max(c["years"]) if c["years"] else None
        out.append(c)
    return sorted(out, key=lambda c: (-c["n"], c["company"]))


def topic(name):
    """Which companies ask this topic, and how often."""
    sts, facts = _all()
    by_id = {s["id"]: s for s in sts}
    per_company = defaultdict(lambda: {"hits": set(), "quotes": []})
    totals = defaultdict(int)
    for s in sts:
        totals[s["company"]] += 1
    for f in facts:
        if f["kind"] == "topic" and f["value"] == name:
            s = by_id[f["story_id"]]
            entry = per_company[s["company"]]
            entry["hits"].add(s["id"])
            entry["quotes"].append(f["quote"])
    rows = [{"company": c, "count": len(e["hits"]), "total": totals[c], "quotes": e["quotes"][:3]}
            for c, e in per_company.items()]
    return sorted(rows, key=lambda r: (-r["count"] / r["total"], r["company"]))


def all_topics():
    _, facts = _all()
    counts = defaultdict(set)
    for f in facts:
        if f["kind"] == "topic":
            counts[f["value"]].add(f["story_id"])
    return sorted(((t, len(ids)) for t, ids in counts.items()), key=lambda x: -x[1])


def compare(a, b):
    """Two playbooks side by side, topic by topic."""
    pa, pb = plan.playbook(a), plan.playbook(b)

    def share(pbk):
        return {t["value"]: t["count"] / pbk["n"] for t in pbk["topics"]} if pbk["n"] else {}

    sa, sb = share(pa), share(pb)
    rows = []
    for t in sorted(set(sa) | set(sb), key=lambda t: -(sa.get(t, 0) + sb.get(t, 0))):
        rows.append({"topic": t, "a": sa.get(t, 0), "b": sb.get(t, 0)})
    common = [r["topic"] for r in rows if r["a"] and r["b"]]
    return {"a": pa, "b": pb, "rows": rows, "common": common}


def prep_plan(company, days, weak=(), today=None):
    """A day-by-day plan built only from what people reported.

    Topics seen in more stories get more days, weak topics get a boost,
    and the last days are kept for mocks and revision.
    """
    pb = plan.playbook(company)
    if not pb["n"] or days < 1:
        return None
    today = today or datetime.date.today()
    weak = set(weak)

    weights = []
    for t in pb["topics"]:
        w = t["count"] / pb["n"]
        if t["value"] in weak:
            w *= 2
        weights.append((t["value"], w, t["count"]))
    weights.sort(key=lambda x: -x[1])

    review_days = 1 if days <= 4 else 2
    study_days = max(days - review_days, 1)
    total = sum(w for _, w, _ in weights) or 1

    # every topic gets at least part of a day; big ones get more
    blocks = []
    for name, w, count in weights:
        share = max(0.5, study_days * w / total)
        blocks.append({"topic": name, "days": share, "count": count, "weak": name in weak})

    schedule, day, used = [], 0, 0.0
    for b in blocks:
        start = math.floor(used)
        used += b["days"]
        end = max(start, math.ceil(used) - 1)
        if start >= study_days:
            break
        end = min(end, study_days - 1)
        b["from"] = today + datetime.timedelta(days=start)
        b["to"] = today + datetime.timedelta(days=end)
        schedule.append(b)

    rounds = [r["value"] for r in pb["rounds"]]
    final = []
    for i in range(review_days):
        when = today + datetime.timedelta(days=study_days + i)
        if i == review_days - 1:
            final.append({"date": when, "task": "Light revision, sleep early. Re-read the mistakes list below."})
        else:
            final.append({"date": when, "task": "Timed mock of the rounds people reported: " + " → ".join(rounds)})

    return {
        "pb": pb,
        "days": days,
        "schedule": schedule,
        "final": final,
        "resources": pb["resources"][:5],
        "mistakes": pb["mistakes"][:5],
        "not_covered": sorted(weak - {w[0] for w in weights}),
    }


def story_view(story_id):
    """One story as facts. Raw text is never shown, it can hold identifying details."""
    s = db.story(story_id)
    if not s or not s["consent_summary"]:
        return None
    facts = db.facts_for([story_id])
    grouped = defaultdict(list)
    for f in facts:
        grouped[f["kind"]].append(f)
    grouped["round"].sort(key=lambda f: f["position"])
    return {"story": s, "facts": grouped,
            "rounds": [f["value"] for f in grouped["round"] if f["value"] in ROUND_TYPES]}
