# PrepMap

Find seniors who already cracked the internship you're preparing for, and get a prep plan built from what they actually said.

Built for the DEV Hacktoberfest Weekend Challenge: Build for a Friend.

## What it does

No login, no signup. Open it and use it.

- **Landing page** that explains the idea, live stats, and how it works.
- **Find people**: ask in plain words ("Google SWE intern via campus, weak at graphs"). Gemma turns it into company, route and topics, and you get seniors who went through it, with ✓/✗ reasons for every match.
- **Explore**: every company and program as a card, filterable by route (campus, off-campus, referral, PPO) and outcome.
- **Playbooks**: rounds in order, topics with "3 of 5 stories" counts, resources, mistakes, what people wish they knew, timeline, and gaps. Every line opens to the exact sentence it came from.
- **Who to ask at each stage**: for every round, the people who went through it and agreed to be contacted.
- **Personal prep plan**: pick days left and weak topics, get a day-by-day plan built only from real stories, with a checklist saved in your browser and a print/PDF view.
- **Compare**: two companies side by side, and the topics you can prepare once for both.
- **Topic pages**: weak at DP? See which companies ask it most, with quotes.
- **Story pages**: one person's process as facts (never the raw text).
- **Anonymous questions board**: ask and answer without an account.
- **Share your story**: paste it, see what Gemma extracted, fix it, choose consent, get a delete link.
- **Honest evaluation**: `/eval` runs a leave-one-out test against a generic plan.

## How it works

```
story (WhatsApp-style text or form answers)
   -> Gemma extracts rounds, topics, resources, mistakes, advice + a quote for each
   -> quote check: if the quote is not really in the text, the fact is dropped
   -> the person reviews and approves
   -> SQLite
   -> playbook, people search, gaps, eval
```

The model reads. Plain code counts, ranks and checks.

## Run it locally (private mode)

Real stories stay on your machine with local Gemma.

```bash
# 1. install Ollama from https://ollama.com, then:
ollama pull gemma3:4b

# 2. run PrepMap
pip install -r requirements.txt
python app.py            # http://localhost:5000
```

Import Google Form answers: `python import_form.py responses.csv` (edit `COLUMNS` in that file to match your form headers).

Run the evaluation: `python evaluate.py`

## Public demo

The hosted demo (Render) uses made-up sample stories from `seed.py` and Gemma through Google AI Studio. It never stores anything. See `render.yaml`.

Settings (environment variables):

| name | default | meaning |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama`, `gemini` or `mock` |
| `OLLAMA_MODEL` | `gemma3:4b` | any Gemma tag you pulled |
| `GEMINI_MODEL` | `gemma-4-26b-a4b-it` | Gemma model on AI Studio (falls back to `gemma-3-27b-it`) |
| `DEMO_MODE` | off | `1` = sample data, no saving |

## Privacy

- No name or contact is stored unless the person ticks "juniors may contact me".
- Every saved story gets a delete link.
- No scraping. Stories come only from people who choose to share.

## Project layout

```
app.py          routes
db.py           tables and queries
llm.py          talks to Gemma (Ollama, AI Studio or mock)
extract.py      story -> grounded facts
plan.py         playbook, gaps, people matching
insights.py     explore, topics, compare, prep plans, story pages
evaluate.py     leave-one-out and retrieval tests
import_form.py  Google Form CSV import
seed.py         fake demo data
```

## License

MIT
