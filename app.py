import datetime
import os

from flask import Flask, abort, redirect, render_template, request, url_for

import db
import evaluate
import extract
import insights
import llm
import plan

app = Flask(__name__)
DEMO = os.environ.get("DEMO_MODE") == "1"
MAX_TEXT = 4000

db.init()
if DEMO:
    import seed
    seed.load_demo()


@app.context_processor
def globals_():
    return {"demo": DEMO, "model": llm.describe(), "topics_list": extract.TOPICS}


# --- pages that explain and browse -------------------------------------------

@app.get("/")
def home():
    return render_template("home.html", s=insights.stats(), companies=db.companies()[:6])


@app.get("/about")
def about():
    return render_template("about.html")


@app.get("/explore")
def explore():
    route = request.args.get("route") or None
    outcome = request.args.get("outcome") or None
    return render_template("explore.html", cards=insights.explore(route, outcome), route=route, outcome=outcome)


@app.get("/company/<name>")
def company(name):
    pb = plan.playbook(name)
    if not pb["n"]:
        abort(404)
    return render_template("company.html", pb=pb, questions=db.questions(name)[:5])


@app.get("/story/<int:story_id>")
def story(story_id):
    view = insights.story_view(story_id)
    if not view:
        abort(404)
    return render_template("story.html", v=view)


@app.get("/topics")
def topics():
    return render_template("topics.html", topics=insights.all_topics())


@app.get("/topic/<name>")
def topic(name):
    if name not in extract.TOPICS:
        abort(404)
    return render_template("topic.html", name=name, rows=insights.topic(name))


@app.get("/compare")
def compare():
    names = [c["company"] for c in db.companies()]
    a, b = request.args.get("a"), request.args.get("b")
    result = insights.compare(a, b) if a and b and a != b else None
    return render_template("compare.html", names=names, a=a, b=b, r=result)


# --- finding people ------------------------------------------------------------

@app.route("/ask", methods=["GET", "POST"])
def ask():
    if request.method == "GET":
        return render_template("ask.html", companies=db.companies())
    question = request.form.get("q", "").strip()[:500]
    if not question:
        return redirect(url_for("ask"))
    companies = [c["company"] for c in db.companies()]
    intent = plan.parse_intent(question, companies)
    people, hidden = plan.match_people(intent)
    for p in people:
        p["message"] = plan.intro_message(p["story"], intent)
    return render_template("results.html", q=question, intent=intent, people=people, hidden=hidden)


# --- personal prep plan --------------------------------------------------------

@app.get("/company/<name>/plan")
def prep_plan(name):
    pb = plan.playbook(name)
    if not pb["n"]:
        abort(404)
    days = request.args.get("days", type=int)
    weak = request.args.getlist("weak")
    if not days:
        return render_template("plan_form.html", pb=pb)
    days = max(1, min(days, 90))
    result = insights.prep_plan(name, days, weak)
    return render_template("plan.html", p=result, weak=weak)


# --- anonymous questions -------------------------------------------------------

@app.route("/questions", methods=["GET", "POST"])
def questions():
    if request.method == "POST":
        text = request.form.get("text", "").strip()[:MAX_TEXT]
        company = request.form.get("company", "").strip() or None
        if len(text) < 10:
            return render_template("questions.html", qs=db.questions(), companies=db.companies(),
                                   error="Please write a little more so seniors can help.")
        qid = db.add_question(text, company)
        return redirect(url_for("question", question_id=qid))
    company = request.args.get("company") or None
    return render_template("questions.html", qs=db.questions(company), companies=db.companies(), company=company)


@app.route("/questions/<int:question_id>", methods=["GET", "POST"])
def question(question_id):
    if request.method == "POST":
        text = request.form.get("text", "").strip()[:MAX_TEXT]
        if len(text) >= 5:
            db.add_answer(question_id, text, request.form.get("by_line", "").strip()[:80] or None)
        return redirect(url_for("question", question_id=question_id))
    q = db.question(question_id)
    if not q:
        abort(404)
    return render_template("question.html", q=q)


# --- sharing a story -------------------------------------------------------------

@app.route("/share", methods=["GET", "POST"])
def share():
    if request.method == "GET":
        return render_template("share.html")
    text = request.form.get("text", "").strip()[:MAX_TEXT]
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
        return "Company or program is required", 400
    year = f.get("year", "").strip()
    story = {
        "company": company,
        "role": f.get("role", "").strip() or None,
        "year": int(year) if year.isdigit() else None,
        "outcome": f.get("outcome") or "unknown",
        "route": f.get("route") or "unknown",
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


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.template_filter("day")
def day(d):
    return d.strftime("%a %d %b") if isinstance(d, datetime.date) else d


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
