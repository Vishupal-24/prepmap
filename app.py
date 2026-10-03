import os

from flask import Flask, abort, redirect, render_template, request, url_for

import db
import evaluate
import extract
import llm
import plan

app = Flask(__name__)
DEMO = os.environ.get("DEMO_MODE") == "1"

db.init()
if DEMO:
    import seed
    seed.load_demo()


@app.context_processor
def globals_():
    return {"demo": DEMO, "model": llm.describe()}


@app.get("/")
def home():
    return render_template("home.html", companies=db.companies())


@app.post("/ask")
def ask():
    question = request.form.get("q", "").strip()
    if not question:
        return redirect(url_for("home"))
    companies = [c["company"] for c in db.companies()]
    intent = plan.parse_intent(question, companies)
    people, hidden = plan.match_people(intent)
    for p in people:
        p["message"] = plan.intro_message(p["story"], intent)
    return render_template("results.html", q=question, intent=intent, people=people, hidden=hidden)


@app.get("/company/<name>")
def company(name):
    pb = plan.playbook(name)
    if not pb["n"]:
        abort(404)
    return render_template("company.html", pb=pb)


@app.route("/share", methods=["GET", "POST"])
def share():
    if request.method == "GET":
        return render_template("share.html")
    text = request.form.get("text", "").strip()
    if len(text) < 40:
        return render_template("share.html", error="Please paste a bit more of the story.", text=text)
    try:
        result = extract.extract(text)
    except Exception as e:
        return render_template("share.html", error=f"The model could not read this: {e}", text=text)
    return render_template("review.html", text=text, r=result)


@app.post("/share/save")
def save():
    if DEMO:
        return render_template("saved.html", demo_only=True)
    f = request.form
    keep = set(f.getlist("keep"))
    facts = [(k, v, q) for i, (k, v, q) in enumerate(zip(f.getlist("kind"), f.getlist("value"), f.getlist("quote")))
             if str(i) in keep]
    company = f.get("company", "").strip()
    if not company:
        return "Company is required", 400
    year = f.get("year", "").strip()
    story = {
        "company": company,
        "role": f.get("role", "").strip() or None,
        "year": int(year) if year.isdigit() else None,
        "outcome": f.get("outcome") or "unknown",
        "source": "paste",
        "raw_text": f.get("text"),
        "name": f.get("name", "").strip() or None,
        "contact": f.get("contact", "").strip() or None,
        "proof_url": f.get("proof_url", "").strip() or None,
        "consent_summary": 1 if f.get("consent_summary") else 0,
        "consent_contact": 1 if f.get("consent_contact") else 0,
        "approved": 1,  # the person reviewing is the person sharing
    }
    _, token = db.save_story(story, facts)
    return render_template("saved.html", token=token, company=company)


@app.get("/delete/<token>")
def delete(token):
    gone = db.delete_story(token)
    return render_template("saved.html", deleted=bool(gone))


@app.get("/eval")
def eval_page():
    rows = evaluate.leave_one_out()
    return render_template("eval.html", rows=rows, s=evaluate.summary(rows), r=evaluate.retrieval_test())


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
