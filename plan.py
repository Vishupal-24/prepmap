"""Turn many stories into one playbook, find what is missing, and find people to ask."""
import datetime
import re
from collections import defaultdict

import db
import llm
from extract import ROUND_TYPES, TOPICS, _norm, _pick


def confidence(n):
    if n < 3:
        return "low"
    if n < 7:
        return "medium"
    return "good"


def playbook(company):
    sts = db.stories(company)
    ids = [s["id"] for s in sts]
    by_id = {s["id"]: s for s in sts}
    facts = db.facts_for(ids)

    # kind -> value -> list of (story, quote)
    grouped = defaultdict(lambda: defaultdict(list))
    for f in facts:
        grouped[f["kind"]][f["value"]].append((by_id[f["story_id"]], f["quote"]))

    def ranked(kind):
        items = []
        for value, refs in grouped[kind].items():
            story_ids = {s["id"] for s, _ in refs}
            items.append({"value": value, "count": len(story_ids), "refs": refs})
        return sorted(items, key=lambda x: (-x["count"], x["value"]))

    # typical round order: average position of each round type
    order = defaultdict(list)
    for f in facts:
        if f["kind"] == "round":
            order[f["value"]].append(f["position"])
    rounds = sorted(ranked("round"), key=lambda r: sum(order[r["value"]]) / len(order[r["value"]]))

    outcomes = defaultdict(int)
    for s in sts:
        outcomes[s["outcome"] or "unknown"] += 1

    return {
        "company": company,
        "n": len(sts),
        "confidence": confidence(len(sts)),
        "outcomes": dict(outcomes),
        "rounds": rounds,
        "topics": ranked("topic"),
        "resources": ranked("resource"),
        "mistakes": ranked("mistake"),
        "advice": ranked("advice"),
        "timeline": ranked("timeline"),
        "gaps": gaps(len(sts), grouped, outcomes),
    }


# things a junior always wants to know, and the question to ask if nobody said it
CHECKLIST = [
    ("round", "OA", "What was the OA like: platform, number of questions, time?"),
    ("round", "manager chat", "Was there a manager or behavioral round, and what did they ask?"),
    ("timeline", None, "How long did the whole process take from OA to result?"),
    ("resource", None, "Which resources actually helped you, and which were a waste?"),
    ("mistake", None, "What would you do differently if you prepared again?"),
]


def gaps(n, grouped, outcomes):
    found = []
    for kind, value, question in CHECKLIST:
        hits = len(grouped[kind].get(value, [])) if value else sum(len(v) for v in grouped[kind].values())
        if hits < 2:
            found.append({"missing": value or kind, "question": question, "mentions": hits})
    if n and outcomes.get("rejected", 0) == 0:
        found.append({"missing": "rejected stories",
                      "question": "Did anyone not make it? What went wrong in their rounds?",
                      "mentions": 0})
    return found


# --- finding people -----------------------------------------------------------

INTENT_PROMPT = """A student asks for help preparing for an internship. Read the question and return only JSON:
{{"company": str|null, "role": str|null, "topics": [str], "deadline": str|null}}
topics must come from: {topics}
Question: \"\"\"{q}\"\"\"
"""


def parse_intent(question, known_companies):
    """Try the model, fall back to simple matching so search never breaks."""
    intent = {"company": None, "role": None, "topics": [], "deadline": None}
    try:
        raw = llm.generate_json(INTENT_PROMPT.format(topics=", ".join(TOPICS), q=question))
        intent.update({k: raw.get(k) for k in intent if raw.get(k)})
        intent["topics"] = [t for t in (_pick(t, TOPICS) for t in intent["topics"] or []) if t]
    except Exception:
        pass
    q = _norm(question)
    if not intent["company"]:
        for c in known_companies:
            if _norm(c) in q:
                intent["company"] = c
    if not intent["topics"]:
        intent["topics"] = [t for t in TOPICS if re.search(r"\b" + re.escape(_norm(t)) + r"\b", q)]
    return intent


def match_people(intent, limit=5):
    this_year = datetime.date.today().year
    sts = db.stories()
    facts = db.facts_for([s["id"] for s in sts])
    topics_of = defaultdict(set)
    rounds_of = defaultdict(set)
    for f in facts:
        if f["kind"] == "topic":
            topics_of[f["story_id"]].add(f["value"])
        elif f["kind"] == "round":
            rounds_of[f["story_id"]].add(f["value"])

    want_company = _norm(intent.get("company"))
    want_role = _norm(intent.get("role"))
    want_topics = set(intent.get("topics") or [])

    results = []
    for s in sts:
        score, why = 0, []
        if want_company:
            if _norm(s["company"]) == want_company:
                score += 5
                why.append((True, f"Went through {s['company']}"))
            else:
                why.append((False, f"Different company ({s['company']})"))
        if s["outcome"] == "offer":
            score += 2
            why.append((True, "Got the offer"))
        elif s["outcome"] == "rejected":
            score += 1
            why.append((True, "Was rejected, can tell you what went wrong"))
        if want_role and s["role"] and want_role in _norm(s["role"]):
            score += 1
            why.append((True, f"Same role: {s['role']}"))
        common = want_topics & topics_of[s["id"]]
        if common:
            score += len(common)
            why.append((True, "Faced " + ", ".join(sorted(common))))
        if s["year"]:
            if this_year - s["year"] <= 1:
                score += 1
                why.append((True, f"Recent ({s['year']})"))
            elif this_year - s["year"] >= 3:
                why.append((False, f"Older experience ({s['year']})"))
        why.append((bool(s["proof_url"]), "Evidence attached" if s["proof_url"] else "Self-reported"))
        if score > 0:
            results.append({"story": s, "score": score, "why": why,
                            "rounds": sorted(rounds_of[s["id"]], key=ROUND_TYPES.index)})

    results.sort(key=lambda r: -r["score"])
    contactable = [r for r in results if r["story"]["consent_contact"]]
    hidden = len(results) - len(contactable)
    return contactable[:limit], hidden


def intro_message(story, intent, me="a junior from PEC"):
    """Plain template on purpose: the student edits and sends it themselves."""
    company = story["company"]
    topics = ", ".join(intent.get("topics") or []) or "the interview rounds"
    name = (story.get("name") or "").split(" ")[0] or "there"
    return (f"Hi {name}, I'm {me} preparing for the {company} internship. "
            f"I saw you went through their process in {story['year'] or 'an earlier year'}. "
            f"Could you share 10 minutes on how you prepared for {topics}? "
            f"Totally fine if you're busy. Thank you!")
