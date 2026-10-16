# GiuCorp AI Outreach

Small PydanticAI workflow that reads eligible prospects from the existing GiuCorp PostgreSQL database, drafts one personalized English email through OpenRouter, previews it, and optionally sends it through Gmail.

## Why PydanticAI

The project is designed to run in the same Python 3.14 environment as the GiuCorp Board. PydanticAI supports Python 3.14 and provides a native OpenRouter provider, so there is no separate CrewAI environment.

## Safety model

The LLM does **not** receive Gmail credentials, does **not** get a database tool, and does **not** decide who receives mail. Python selects prospects, sends a bounded snapshot of prospect context to the model, validates the structured output, and handles delivery.

The CLI is dry-run by default. Real delivery requires `--send`.

Prospects are eligible when they:

- have status `new`;
- have an email address;
- do not already have an AI outreach email activity recorded.

A successful send creates an `Activity` with the `[AI_OUTREACH]` prefix and changes a new prospect to `contacted`. This provides simple deduplication and an audit trail.

## Setup on macOS, Python 3.14

From the project root, use your normal GiuCorp virtual environment:

```bash
source .venv/bin/activate
python --version
```

Expected:

```text
Python 3.14.x
```

Install the web project plus the AI extra:

```bash
python -m pip install -e ".[ai]"
```

Alternatively:

```bash
python -m pip install -e .
python -m pip install -r ai_outreach/requirements.txt
```

Then:

```bash
cp .env.agent.example .env.agent
```

Your normal `.env` continues to hold PostgreSQL configuration. If Docker exposes Postgres on port 5433, keep:

```env
POSTGRES_PORT=5433
```

## OpenRouter

Set your key and any OpenRouter model slug:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-5.4-mini
```

The agent uses PydanticAI's native OpenRouter provider. The output uses prompted structured output so it can work with a broad range of OpenRouter models, including models without reliable tool calling. Pydantic validates the returned `subject` and `body` before the message can be sent.

## Gmail authentication

This implementation uses Gmail SMTP over TLS with a dedicated Google App Password for simplicity. Never put your normal Google password in `.env.agent`.

For a larger or public deployment, migrate delivery to Gmail OAuth/API.

## Usage

Preview one prospect without sending:

```bash
python -m ai_outreach --limit 1
```

Preview five:

```bash
python -m ai_outreach --limit 5
```

Send, bounded by `OUTREACH_DAILY_LIMIT`:

```bash
python -m ai_outreach --limit 15 --send
```

Target one prospect:

```bash
python -m ai_outreach --prospect-id 42
python -m ai_outreach --prospect-id 42 --send
```

## Copy rules

The agent is instructed to:

- write in natural professional English;
- never use em dashes;
- avoid fabricated facts and fake familiarity;
- use only facts already stored for the prospect;
- avoid hype, fake urgency, generic AI language, and emojis;
- keep the body concise;
- end with a low-friction CTA.

Database content is serialized as bounded JSON and explicitly treated as untrusted data.
