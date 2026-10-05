# PrepMap

Find seniors who already cracked the internship you're preparing for, and get a prep plan built from what they actually said.

Built for the DEV Hacktoberfest Weekend Challenge: Build for a Friend.

## What it does

- **Ask in plain words**: "Google SWE intern OA next week, weak at graphs". Gemma turns it into company, role and topics.
- **People you can ask**: seniors who went through that process, with a clear "why this person" (and why not). Only people who said yes to contact are shown. Everyone else counts anonymously.
- **Playbook per company or program** (Google, Stripe, Amazon ML Summer School, GSoC...): rounds in the usual order, topics with "3 of 5 stories" counts, resources, mistakes, and what people wish they knew. Every line opens to the exact sentence it came from.
- **Who to ask at each stage**: for every round (OA, coding, manager chat), the people who went through it and agreed to be contacted.
- **Same route as you**: stories record how people got in (campus, off-campus, referral, PPO), and matches show when someone took the same route.
- **Gaps**: what nobody has told us yet, and the question to ask a senior.
- **Honest numbers**: a leave-one-out test on the `/eval` page compares the company plan with a generic one.

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
evaluate.py     leave-one-out and retrieval tests
import_form.py  Google Form CSV import
seed.py         fake demo data
```

## License

MIT
