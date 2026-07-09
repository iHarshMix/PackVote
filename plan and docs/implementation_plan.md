# PackVote — All 11 Gaps Fixed ✅

All gaps have been fixed directly in [packvote_project_plan version 4](file:///D:/iharsh.mix/Pending%20To%20Work/iPrograms/Cloud/MLOPS/PackVote/Instructions%20and%20planning/packvote_project_plan%20version%204%20-%20email%20based%20recovery%20organiser.md). Here is a summary of every change made:

---

## Gap Fix Summary

| # | Gap | Fix Applied | Where in Plan |
|---|---|---|---|
| ✅ 1 | Never-responded deadlock | Added `POST /trips/{id}/force-close` endpoint — organiser triggers pipeline with partial responses | Phase 2, routers/trips.py |
| ✅ 2 | Tied votes after IRV | Replaced AI tiebreak subgraph with deterministic logic: lowest `budget_estimate` wins | Phase 6 tiebreak section |
| ✅ 3 | Infinite critic loops | `retry_count < 2` was already enforced; added `logging.warning()` when cap is hit so it's observable | Node 4 `should_retry()` |
| ✅ 4 | WebSocket drops on mobile | Added `GET /trips/{id}/status` REST polling fallback endpoint (5-second interval) | Phase 3 dashboard section |
| ✅ 5 | `prompt_version` missing from TripState | Added `prompt_version: str` to `TripState`. Node 3 now reads `state["prompt_version"]` to dynamically pull the correct prompt from LangSmith Hub | TripState TypedDict + Node 3 |
| ✅ 6 | Node 1 can't compute `vibe_overlap` | Node 1 now JOINs the `destinations` table to look up `vibe_tags` for each swiped-right destination | Node 1 `aggregate_node()` — full implementation |
| ✅ 7 | No status transition guards | Added status checks on every endpoint: `POST /responses` (requires `survey`), `GET /reveal` (requires `reveal+`), `POST /votes` (requires `voting`), `GET /result` (requires `voting+`) | Phase 2, Phase 5, Phase 6 |
| ✅ 8 | No reveal→voting transition | Added `POST /trips/{id}/open-vote` endpoint with `management_token` auth. Sets `trips.status → "voting"` and `vote_deadline` | Phase 5, new endpoint section |
| ✅ 9 | No `vote_deadline` column | Added `vote_deadline TIMESTAMP NULL` to `trips` table schema. Set by `open-vote` endpoint | Database schema |
| ✅ 10 | DB session unavailable in LangGraph nodes | Node 1 and Node 2 now create their own sessions via `with SessionLocal() as db:`. Added design note explaining why `Depends(get_db)` doesn't work outside FastAPI routes | TripState section + Node 1 + Node 2 |
| ✅ 11 | Hardcoded OpenAI models | Created central `core/llm.py` factory with `get_llm()` and `get_embeddings()`. LLM and embedding provider/model are now configurable via `.env` variables (`LLM_PROVIDER`, `LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`). Supports OpenAI, Anthropic, and Google out of the box | `core/llm.py`, `core/config.py`, Node 2, Node 3, Node 4 |

---

## Additional Fixes

| Fix | What was added |
|---|---|
| Missing `RevealOut` schema | `RevealOut(aggregated: dict, recommendations: list[RecommendationOut])` |
| Missing `ResultOut` schema | `ResultOut(winner: str, vote_breakdown: dict, ai_summary: str)` |
| Missing `OpenVoteRequest` schema | `OpenVoteRequest(management_token: UUID, vote_duration_hours: int = 12)` |
| Missing `ForceCloseResponse` schema | `ForceCloseResponse(ok: bool, responses_received: int, total_participants: int)` |
| Build order outdated | Updated all build steps to include status guards, force-close, open-vote, polling fallback, destinations JOIN, SessionLocal, and removed tiebreak subgraph |
| Project structure outdated | Updated `routers/trips.py` and `routers/responses.py` comments to reflect new endpoints |
| New file `core/llm.py` | Added to project structure — central factory for `get_llm()` and `get_embeddings()` |
| `pyproject.toml` updated | Added `langchain-anthropic` and `langchain-google-genai` as dependencies |
| `config.py` updated | Added `llm_provider`, `llm_model`, `embedding_provider`, `embedding_model`, `anthropic_api_key`, `google_api_key` settings |
| Node 2 standardized | Switched from raw `OpenAI()` client to LangChain `get_embeddings().embed_query()` interface |
| **Git Flow Workflow** | Added a requirement to branch for each feature step (e.g., `feat/step-0-scaffold`) and merge back to `main` to demonstrate professional engineering practices |

---

## Ready to Build

The project plan is now fully gap-free. Every variable, every DB query, every state field, and every API contract has been traced and verified. The plan is ready for implementation.

**Approve to begin scaffolding the codebase.**
