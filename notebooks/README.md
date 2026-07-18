# Course Notebooks

Seven notebooks that build up the OpenAI Agents SDK concept by concept, ending with a direct bridge into the capstone repo (`agent.py`, `app.py`, etc. one level up).

Each notebook is self-contained -- its first code cell installs `openai-agents` and asks for an API key via `getpass`, so any of them can be opened fresh (e.g. copied individually into Colab or whatever platform you're teaching on) without depending on another notebook having run first in the same session.

## Suggested pacing

| Day | Notebooks | Theme |
|---|---|---|
| Day 1 | `00_setup`, `01_your_first_agent`, `02_giving_your_agent_tools`, `03_seeing_how_the_agent_thinks` | Core concepts: what an agent is, tools, and watching multi-tool iteration happen |
| Day 2 | `04_hosted_tools`, `05_multi_turn_conversations`, `06_from_notebook_to_telegram_bot` | Built-in capabilities, memory, then straight into the capstone deployment (repo root `README.md`) |

`06_from_notebook_to_telegram_bot.ipynb` is the hinge point -- it doesn't teach anything new, it just maps each notebook's concept onto where it actually lives in `agent.py`/`app.py`, so the jump from "notebook exercises" to "real file in a folder" isn't a leap.

## Verification note

Every code cell here was syntax-checked and executed (with only the live OpenAI network calls mocked out) against the real, installed `openai-agents` package before being committed -- not just written from memory. The one thing that can't be verified without a live API key is the *content* of the model's actual replies, which is fine: that's for learners to see for themselves when they run it.
