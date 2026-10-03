"""Made-up sample stories for the public demo only.

These are NOT real people or real interviews. They exist so the hosted demo
has something to show. Real stories live in a local database, never here.
"""
import db
from extract import from_form_row

SAMPLES = [
    # company, role, year, outcome, rounds, topics, timeline, resources, mistake, advice, contact ok
    ("Google", "SWE intern", 2025, "offer", "OA, coding, coding", "graphs, BFS/DFS, dynamic programming, arrays",
     "about 3 weeks from OA to result", "LeetCode Google tag, Striver graph series",
     "Spent too long on the first OA question", "Talk out loud in the coding rounds", True),
    ("Google", "SWE intern", 2025, "rejected", "OA, coding, coding", "dynamic programming, strings, hashing",
     "2 weeks", "NeetCode 150", "Did not test edge cases before saying done",
     "Practice writing code in a plain doc, no autocomplete", True),
    ("Google", "STEP intern", 2024, "offer", "OA, coding, coding", "trees, recursion/backtracking, arrays",
     "a month", "Codeforces div 2 contests", "Ignored time complexity until asked",
     "State complexity before they ask", False),
    ("Google", "SWE intern", 2025, "offer", "OA, coding, coding, manager chat", "graphs, shortest paths, heaps",
     "3 weeks", "LeetCode Google tag", "Panicked on a follow-up question",
     "Follow-ups matter more than the first solution", True),
    ("Google", "SWE intern", 2024, "rejected", "OA", "dynamic programming, bit manipulation",
     "", "", "Started DP prep too late", "Do one DP problem every day for a month before the OA", False),
    ("Google", "STEP intern", 2025, "offer", "OA, coding, coding", "arrays, two pointers, graphs",
     "4 weeks", "Striver SDE sheet", "", "Ask clarifying questions first", False),
    ("Flipkart", "SDE intern", 2025, "offer", "OA, machine coding, CS fundamentals", "low level design, OOP, DBMS",
     "10 days", "Concept && Coding LLD videos", "Wrote everything in one class during machine coding",
     "Practice one machine coding problem in 90 minutes", True),
    ("Flipkart", "SDE intern", 2024, "rejected", "OA, machine coding", "low level design, concurrency",
     "1 week", "", "Did not handle concurrent bookings", "Think about thread safety", False),
    ("Flipkart", "SDE intern", 2025, "offer", "OA, coding, CS fundamentals", "graphs, operating systems, DBMS, SQL",
     "2 weeks", "GFG CS fundamentals notes", "", "Revise OS and DBMS basics, they do ask", True),
    ("Stripe", "SWE intern", 2025, "offer", "OA, coding, project discussion, manager chat",
     "API design, debugging, strings", "5 weeks", "Stripe engineering blog",
     "Wrote clever code instead of clear code", "Readable code and tests beat speed", True),
    ("Stripe", "SWE intern", 2025, "rejected", "OA, coding", "API design, hashing", "3 weeks", "",
     "Did not read the whole problem statement", "Read the spec twice, it is long on purpose", False),
    ("Stripe", "SWE intern", 2024, "offer", "OA, coding, manager chat", "debugging, API design, behavioral",
     "a month", "Stripe operating principles page", "", "Prepare real stories for the manager chat", True),
]


def load_demo():
    if db.stories():
        return
    for i, s in enumerate(SAMPLES, 1):
        company, role, year, outcome, rounds, topics, timeline, resources, mistake, advice, ok = s
        row = {"rounds": rounds, "topics": topics, "timeline": timeline, "resources": resources,
               "mistake": mistake, "advice": advice}
        story = {"company": company, "role": role, "year": year, "outcome": outcome, "source": "sample",
                 "raw_text": None, "name": f"Demo senior {i}" if ok else None,
                 "contact": "sample only, not a real person" if ok else None,
                 "proof_url": None, "consent_summary": 1, "consent_contact": 1 if ok else 0, "approved": 1}
        db.save_story(story, from_form_row(row))
