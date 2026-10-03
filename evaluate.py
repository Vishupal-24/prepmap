"""How useful is the playbook, honestly measured.

Leave-one-out: hide one story, build the topic plan from the others,
and check how many of the hidden story's topics the plan covered.
Baseline: the most common topics across *other* companies, same size.
If the company plan does not beat the baseline, the tool is not adding much.

Run: python evaluate.py
"""
import json
import os
from collections import Counter, defaultdict

import db

PLAN_SIZE = 8


def topic_sets():
    sts = db.stories()
    facts = db.facts_for([s["id"] for s in sts])
    topics = defaultdict(set)
    for f in facts:
        if f["kind"] == "topic":
            topics[f["story_id"]].add(f["value"])
    return [(s, topics[s["id"]]) for s in sts if topics[s["id"]]]


def top_topics(sets, k=PLAN_SIZE):
    counts = Counter(t for s in sets for t in s)
    return {t for t, _ in counts.most_common(k)}


def leave_one_out(min_others=2):
    data = topic_sets()
    rows = []
    for i, (story, held) in enumerate(data):
        same = [t for j, (s, t) in enumerate(data) if j != i and s["company"].lower() == story["company"].lower()]
        other = [t for s, t in data if s["company"].lower() != story["company"].lower()]
        if len(same) < min_others:
            continue
        plan = top_topics(same)
        base = top_topics(other) if other else set()
        rows.append({
            "story_id": story["id"],
            "company": story["company"],
            "held_topics": len(held),
            "plan_recall": len(held & plan) / len(held),
            "baseline_recall": len(held & base) / len(held) if base else None,
        })
    return rows


def summary(rows):
    if not rows:
        return {"n": 0}
    plan = sum(r["plan_recall"] for r in rows) / len(rows)
    base_rows = [r["baseline_recall"] for r in rows if r["baseline_recall"] is not None]
    base = sum(base_rows) / len(base_rows) if base_rows else None
    return {"n": len(rows), "plan_recall": round(plan, 3),
            "baseline_recall": round(base, 3) if base is not None else None,
            "plan_size": PLAN_SIZE}


def retrieval_test(path=os.path.join(os.path.dirname(__file__), "eval", "queries.json")):
    """queries.json: [{"question": "...", "expected_story_ids": [1, 4]}]
    Hit@3 = was at least one expected person in the top 3."""
    import plan
    if not os.path.exists(path):
        return {"n": 0}
    with open(path) as f:
        queries = json.load(f)
    companies = [c["company"] for c in db.companies()]
    hits = []
    for q in queries:
        intent = plan.parse_intent(q["question"], companies)
        found, _ = plan.match_people(intent, limit=3)
        ids = {r["story"]["id"] for r in found}
        hits.append(bool(ids & set(q["expected_story_ids"])))
    return {"n": len(hits), "hit_at_3": round(sum(hits) / len(hits), 3) if hits else None}


if __name__ == "__main__":
    rows = leave_one_out()
    for r in rows:
        print(r)
    print("leave-one-out:", summary(rows))
    print("retrieval:", retrieval_test())
