# 🧳 Multi-Agent Travel Booking System

A multi-agent trip-planning and booking assistant built with **LangGraph**, orchestrating specialist agents for flights, hotels, and itineraries — with automatic failure recovery, iterative budget negotiation, human-in-the-loop approval, long-term personalization, and full observability via **LangSmith**.

Runs completely **offline with zero API keys** out of the box (mock mode), so the entire graph — retries, the negotiation loop, the interrupt/resume flow, booking — can be explored before wiring in real credentials.

---

## Why this project

Most "AI agent" demos are a single LLM calling a couple of tools in a loop. This project is instead a small case study in the harder, more realistic parts of building agentic systems:

- What happens when a tool call comes back empty?
- What happens when the result violates a hard constraint (budget)?
- Where does a human need to stay in the loop before anything irreversible happens?
- How does the system remember a user across sessions, not just within one?

Each of those questions maps to a specific piece of the graph below, rather than being hand-waved away.

---

## Architecture

```
                         ┌──────────────┐
                         │   Traveler   │
                         │   request    │
                         └──────┬───────┘
                                ▼
                         ┌──────────────┐
                         │  Supervisor  │  routes & decides if the
                         │    agent     │  itinerary agent is needed
                         └──────┬───────┘
                     ┌──────────┼──────────┐
                     ▼          ▼          ▼         (parallel — Send API)
              ┌───────────┐┌───────────┐┌──────────────┐
              │  Flight   ││   Hotel   ││  Itinerary   │
              │  agent    ││   agent   ││    agent     │
              │ (retry /  ││ (retry /  ││ (RAG + LLM)  │
              │ fallback) ││ fallback) ││              │
              └─────┬─────┘└─────┬─────┘└──────┬───────┘
                     └────────────┼─────────────┘
                                  ▼
                         ┌──────────────────┐
                         │  Budget           │◄───┐  over budget →
                         │  aggregator       │    │  renegotiate hotel
                         └────────┬──────────┘    │  (max 3 rounds)
                                  │  within budget └────────┘
                                  ▼
                         ┌──────────────────┐
                         │  Human approval   │  ← interrupt(), pauses
                         │  (interrupt)      │    here until resumed
                         └────────┬──────────┘
                        approve  │  reject
                            ▼    └──────► END
                    ┌──────────────┐
                    │   Booking    │
                    │    agent     │
                    └──────┬───────┘
                           ▼
                          END
```

Each of `flight_agent` / `hotel_agent` is its own **compiled subgraph** with an internal `search → retry/fallback` loop, so a bad or empty API response degrades the result gracefully instead of crashing the whole run.

---

## Features

| Capability | Implementation |
|---|---|
| 🔀 Parallel agent orchestration | `Send` API fans out to flight/hotel/itinerary agents concurrently |
| 🔁 Automatic failure recovery | Each specialist subgraph retries with relaxed constraints, then falls back gracefully |
| 💸 Iterative budget negotiation | Aggregator loops back to renegotiate the hotel tier, bounded to 3 rounds |
| 🧍 Human-in-the-loop approval | `interrupt()` / `Command(resume=...)` pauses before any booking is made |
| 📚 Retrieval-augmented itinerary | TF-IDF retrieval over destination guides feeds the itinerary LLM call |
| 🔌 MCP client integration | Optional MCP-based flight search, pluggable alongside a plain REST tool |
| 🧠 Short- & long-term memory | Per-session state + a cross-session `Store` that remembers traveler preferences |
| 💾 Crash-safe persistence | SQLite checkpointing — an interrupted run survives a process restart |
| 📡 Live streaming UI | Streamlit app streams each node's progress in real time |
| 🔍 Full observability | Every run, retry, and loop iteration traced in LangSmith |

---

## Tech stack

- **Orchestration:** LangGraph (`StateGraph`, subgraphs, `Send`, `interrupt`, checkpointing, `Store`)
- **LLM:** Gemini 2.5 Flash (free tier via Google AI Studio) — swappable via `config.py`
- **Flight/hotel data:** Amadeus Self-Service API (sandbox test environment)
- **Retrieval:** scikit-learn TF-IDF over a local markdown corpus
- **Persistence:** SQLite (`langgraph-checkpoint-sqlite`)
- **Observability:** LangSmith
- **UI:** Streamlit
- **Testing:** pytest, fully mocked — no API keys needed to run the suite

---

## Getting started

```bash
git clone <this-repo>
cd travel_booking_agent
pip install -r requirements.txt
cp .env.example .env    # fill in keys, or leave blank to stay in mock mode
```

**Getting free API keys:**
- **Gemini** — an API key from [Google AI Studio](https://aistudio.google.com/) (free tier, no card required)
- **Amadeus** — register at [developers.amadeus.com](https://developers.amadeus.com/) for a Self-Service key (free `test` environment, sandbox inventory, no real payment)

**Run it:**

```bash
streamlit run app.py     # the full UI
python graph.py          # a quick non-UI smoke test in the terminal
pytest tests/            # automated test suite (always runs in mock mode)
```

To use the optional MCP path for flight search instead of the plain REST tool, run a community Amadeus MCP server and set `AMADEUS_MCP_URL` or `AMADEUS_MCP_COMMAND` in `.env`. If neither is set, `flight_agent.py` just uses the REST tool — the MCP path is additive, not required.

> **Note:** even with real Amadeus keys, this uses the `test` sandbox environment. Bookings created by `booking_agent.py` are sandbox confirmations, not real tickets.

---

## Project structure

```
travel_booking_agent/
├── agents/
│   ├── supervisor.py       # routing decision + parallel fan-out
│   ├── flight_agent.py     # subgraph: search + retry/fallback
│   ├── hotel_agent.py      # subgraph: search + retry/fallback
│   ├── itinerary_agent.py  # RAG + LLM day-plan writeup
│   ├── aggregator.py       # budget check + negotiation loop
│   ├── human_approval.py   # interrupt() gate
│   └── booking_agent.py    # writes booking + updates long-term memory
├── tools/
│   ├── llm_client.py       # task-specific LLM calls (mock-or-real switch)
│   ├── rag_tool.py         # TF-IDF retrieval over destination guides
│   ├── amadeus_client.py   # real Amadeus OAuth2 + REST calls
│   ├── flight_mcp.py       # optional MCP-client flight search
│   └── mock_data.py        # deterministic fake offers for mock mode
├── memory/store.py         # long-term memory (cross-session preferences)
├── data/destination_guides/# small RAG corpus
├── tests/test_graph_mock.py
├── state.py                 # shared graph state schema
├── config.py                # env vars, mock-mode detection, model factory
├── persistence.py            # SQLite checkpointer
├── graph.py                  # wires every node together
└── app.py                    # Streamlit UI
```

---

## LangGraph concepts, mapped to code

| Concept | Where it lives |
|---|---|
| Conditional workflows | `agents/aggregator.py → route_after_aggregate` |
| Parallel workflows | `agents/supervisor.py → fan_out` (the `Send` calls) |
| Iterative workflows | The renegotiation loop in `aggregator.py` |
| Subgraphs | `flight_agent.py` / `hotel_agent.py` / `itinerary_agent.py`, added directly as nodes in `graph.py` |
| Tools | `tools/amadeus_client.py`, `tools/mock_data.py` |
| MCP client | `tools/flight_mcp.py` |
| RAG | `tools/rag_tool.py` + `itinerary_agent.py` |
| Human-in-the-loop | `agents/human_approval.py` |
| Persistence / SQLite | `persistence.py`, `agents/booking_agent.py` |
| Short-term memory | `TripState` carried through one thread/run |
| Long-term memory | `memory/store.py` |
| Streaming | `app.py`'s `graph.stream(..., stream_mode="values")` loop |
| LangSmith | Automatic once `LANGSMITH_API_KEY` is set in `.env` |

---

## Known limitations

Worth stating plainly rather than glossing over:

- Itinerary suggestions aren't priced or booked — only flights + hotel count toward the budget.
- The negotiation loop only relaxes the hotel's star-rating floor; flight cabin is retried on empty results but not renegotiated purely for cost.
- Amadeus calls run against the sandbox `test` environment — realistic API shapes, but not live inventory or real payment.
- Long-term memory uses `InMemoryStore` by default, so it resets on process restart; swap in a persistent `Store` implementation for anything long-lived.

---

## License

MIT — use freely, attribution appreciated.
