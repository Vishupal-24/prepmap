"""Turn a messy interview story into facts. Every fact must point at a real sentence."""
import json
import os
import re

import llm

with open(os.path.join(os.path.dirname(__file__), "data", "taxonomy.json")) as f:
    TAXONOMY = json.load(f)

ROUND_TYPES = TAXONOMY["round_types"]
TOPICS = TAXONOMY["topics"]
OUTCOMES = ["offer", "rejected", "no reply", "unknown"]
ROUTES = ["campus", "off-campus", "referral", "PPO", "unknown"]

PROMPT = """You read interview experiences written by students and pull out facts.
The experience can be about a company internship or a program (like Amazon ML Summer School, GSoC or Google STEP).
Rules:
- Only use what the text says. Do not guess.
- For every item copy a short exact quote from the text that supports it.
- round "type" must be one of: {rounds}
- topic "name" must be one of: {topics}
- outcome must be one of: {outcomes}
- route is how they got in, one of: {routes}
- "advice" means what they wish they had known earlier, or tips for juniors
- Use null when the text does not say.

Return only JSON in this shape:
{{"company": str|null, "role": str|null, "year": int|null, "outcome": str, "route": str,
  "rounds": [{{"type": str, "quote": str}}],
  "topics": [{{"name": str, "quote": str}}],
  "resources": [{{"name": str, "quote": str}}],
  "mistakes": [{{"text": str, "quote": str}}],
  "advice": [{{"text": str, "quote": str}}],
  "timeline": {{"text": str, "quote": str}} | null}}

Text:
\"\"\"{text}\"\"\"
"""


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip(" .,'\"")


def quote_ok(quote, text):
    """The quote has to really be in the text, give or take spacing and case."""
    q = _norm(quote)
    return len(q) >= 3 and q in _norm(text)


def _pick(value, allowed):
    for a in allowed:
        if _norm(value) == _norm(a):
            return a
    return None


def extract(text):
    raw = llm.generate_json(PROMPT.format(
        rounds=", ".join(ROUND_TYPES), topics=", ".join(TOPICS),
        outcomes=", ".join(OUTCOMES), routes=", ".join(ROUTES), text=text))
    return validate(raw, text)


def validate(raw, text):
    """Keep what is grounded, report what got dropped."""
    facts, dropped = [], []

    def keep(kind, value, quote):
        if value and quote_ok(quote, text):
            facts.append((kind, value, quote.strip()))
        else:
            dropped.append({"kind": kind, "value": value, "quote": quote})

    for r in raw.get("rounds") or []:
        keep("round", _pick(r.get("type"), ROUND_TYPES), r.get("quote"))
    for t in raw.get("topics") or []:
        keep("topic", _pick(t.get("name"), TOPICS), t.get("quote"))
    for r in raw.get("resources") or []:
        keep("resource", (r.get("name") or "").strip(), r.get("quote"))
    for m in raw.get("mistakes") or []:
        keep("mistake", (m.get("text") or "").strip(), m.get("quote"))
    for a in raw.get("advice") or []:
        keep("advice", (a.get("text") or "").strip(), a.get("quote"))
    tl = raw.get("timeline")
    if isinstance(tl, dict):
        keep("timeline", (tl.get("text") or "").strip(), tl.get("quote"))

    # same topic twice is still one topic
    seen, unique = set(), []
    for f in facts:
        key = (f[0], _norm(f[1]))
        if key not in seen:
            seen.add(key)
            unique.append(f)

    year = raw.get("year")
    story = {
        "company": (raw.get("company") or "").strip() or None,
        "role": (raw.get("role") or "").strip() or None,
        "year": year if isinstance(year, int) else None,
        "outcome": _pick(raw.get("outcome") or "unknown", OUTCOMES) or "unknown",
        "route": pick_route(raw.get("route")),
    }
    return {"story": story, "facts": unique, "dropped": dropped}


def pick_route(value):
    v = _norm(value)
    if "ppo" in v or "pre-placement" in v:
        return "PPO"
    if "refer" in v:
        return "referral"
    if re.search(r"\boff[- ]?campus\b", v):
        return "off-campus"
    if re.search(r"\b(on[- ]?)?campus\b", v):
        return "campus"
    return "unknown"


def from_form_row(row):
    """Form answers are already structured, so the answer itself is the quote."""
    facts = []
    for r in _split(row.get("rounds")):
        t = _pick(r, ROUND_TYPES)
        if t:
            facts.append(("round", t, r))
    for t in _split(row.get("topics")):
        name = _pick(t, TOPICS)
        if name:
            facts.append(("topic", name, t))
    for kind, col in [("resource", "resources"), ("mistake", "mistake"),
                      ("advice", "advice"), ("timeline", "timeline")]:
        val = (row.get(col) or "").strip()
        if val:
            facts.append((kind, val, val))
    return facts


def _split(s):
    # google forms joins ticked boxes with ", "
    return [p.strip() for p in (s or "").split(",") if p.strip()]
