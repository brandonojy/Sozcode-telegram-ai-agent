# Course Notebooks

Eight core notebooks that build up the OpenAI Agents SDK concept by concept, ending with a direct bridge into the capstone repo (`agent.py`, `app.py`, etc. one level up) -- plus one optional bonus notebook.

Each notebook is self-contained -- its first code cell installs `openai-agents` and sets your API key directly as an argument (`set_default_openai_key("sk-...")`, the SDK's own function for this -- no environment variables involved), so any of them can be opened fresh (e.g. copied individually into Colab or whatever platform you're teaching on) without depending on another notebook having run first in the same session. This is intentionally the simplest possible option for a 2-day intro course rather than `getpass`/secret-manager patterns -- just remind learners not to share or commit a notebook with their key still pasted in.

Note for `05_working_with_files.ipynb` specifically: it also constructs a plain `openai.OpenAI()` client directly (for uploading/downloading files, outside the Agents SDK). `set_default_openai_key()` only configures the Agents SDK's own internal client, so that one needs the key passed explicitly too -- `OpenAI(api_key=OPENAI_API_KEY)`, reusing the same variable set in the setup cell.

## Suggested pacing

| Day | Notebooks | Theme |
|---|---|---|
| Day 1 | `00_setup`, `01_your_first_agent`, `02_giving_your_agent_tools`, `03_seeing_how_the_agent_thinks` | Core concepts: what an agent is, tools, and watching multi-tool iteration happen |
| Day 2 | `04_hosted_tools`, `05_working_with_files`, `06_multi_turn_conversations`, `07_from_notebook_to_telegram_bot` | Built-in capabilities, file handling, memory, then straight into the capstone deployment (repo root `README.md`) |

`07_from_notebook_to_telegram_bot.ipynb` is the hinge point -- it doesn't teach anything new, it just maps each notebook's concept onto where it actually lives in `agent.py`/`app.py`, so the jump from "notebook exercises" to "real file in a folder" isn't a leap.

## Bonus (optional): `08_bonus_agentic_browsing.ipynb`

Covers giving an agent **agentic web navigation** -- reading a page, deciding it needs to look at a linked page instead, and fetching that one too -- using [Jina Reader](https://jina.ai/reader/), the exact same service `read_dynamic_webpage` in the capstone's `agent.py` already uses. No new infrastructure: it's pure Python, and the "agentic" part isn't special code, it's just the ordinary tool-calling loop from notebook 03 given a tool whose output includes a list of links to choose from (`X-With-Links-Summary`).

Ends with a real, verifiable multi-hop task (find a fact that's on a *linked* page, not the starting page) so learners can watch the agent choose its own next URL in the trace, not take it on faith. Good for learners who finish early; unlike an earlier draft of this notebook (which used Playwright MCP), this one needs nothing beyond what's already installed, and directly explains the one real gap between it and what's deployed -- the production tool doesn't request the links summary, so the live bot's browsing is effectively single-hop today.

## Verification note

Every code cell here was syntax-checked and executed (with only the live OpenAI network calls mocked out) against the real, installed `openai-agents` package before being committed -- not just written from memory. The one thing that can't be verified without a live API key is the *content* of the model's actual replies, which is fine: that's for learners to see for themselves when they run it.
