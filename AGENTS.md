# AGENTS.md

Guidance for AI coding agents working in this repository. Read this before making changes.

## Project overview

**Online Pixel Dungeon** — a real-time multiplayer roguelike dungeon crawler built on the ruleset of [Shattered Pixel Dungeon](https://github.com/00-Evan/shattered-pixel-dungeon) (SPD). Licensed GPLv3 (see `LICENSE.txt`).

- Real-time, not turn-based: every player and mob acts on a shared server clock (`GAME_LOOP_HZ`, default **40 Hz**, in `backend/app/engine/game/constants.py`).
- **Root `readme.md` is stale** — it claims 20 Hz. Trust `constants.py`, not the readme.
- Public and private (optionally password-protected) rooms; players connect over WebSocket and join a room by `game_id`.
- Multi-floor descent (sewers → prison → caves → city → halls) with bosses every 5th floor; hero classes (Warrior, Mage, Rogue, Huntress, plus Cleric/Duelist work), talents, alchemy, wands, artifacts — modeled closely on the original SPD ruleset.

| Path | Role |
|---|---|
| `backend/` | Python 3.11 / FastAPI authoritative game server (WebSocket + REST) |
| `frontend/` | React 19 + Vite client, canvas renderer, served by nginx in production |
| `shattered-pixel-dungeon/` | **Read-only reference**: full Java source of upstream SPD, used to verify mechanics fidelity. Never modify it (also git-ignored). |
| `docs/` | Design notes + SPD reference (`spd_*.md`, `spd_items/` catalogs, `enemies.txt`, `SPEC_EFFECTS.md`) |

`frontend/README.md` is untouched Vite boilerplate — ignore it.

## Architecture

### Backend (`backend/`)

- Entry point: `backend/app/main.py` — FastAPI app, CORS (allow all), WebSocket endpoint `/ws/game/{game_id}`, and the global asyncio game loop that ticks every `GameInstance`.
- **Server-authoritative state**: all game logic lives on the server. The central class is `GameInstance` in `backend/app/engine/manager.py`, composed from per-concern **mixins** under `backend/app/engine/game/` (movement, combat, items, alchemy, talents, mob AI, serialization, floor generation, etc.).
- Engine layout (`backend/app/engine/`):
  - `game/` — the `GameInstance` mixins, per-mob AI modules (`ai_*.py`), `constants.py` (all tuning constants go here).
  - `dungeon/` — level generation. `spd_levelgen/` is a port of SPD's level generator; `spd_random.py` is a port of SPD's RNG (`com.watabou.utils.Random`, a 48-bit LCG). **Byte-for-byte parity with the Java original is required** so a given seed produces identical layouts — do not change its arithmetic. Guarded by `tests/test_spd_random.py`.
  - `entities/` — Pydantic models for players, mobs, items (`items/`, `weapons/`, `armors/`, `wands/`, `rings/`), buffs, talent data.
  - `systems/` — combat, loot, ballistica (projectile trajectories), rogue preparation.
  - `mechanics/` — e.g. `shadowcaster.py` (field-of-view).
  - `turn/` — **in-progress** turn-based mode (scheduler, actors, upkeep). Rooms default to `GAME_MODE_REALTIME`; `connection_manager.register_game_mode` maps a mode string to a `GameInstance` subclass.
  - `alchemy/`, `talents/` — recipe registry and talent effect handlers.
- API layer (`backend/app/api/`): `connection_manager.py` (rooms, sessions, broadcasting), `ws_handlers.py` + `dispatcher.py` (incoming client messages), `routes.py` (REST: feedback, item catalog, talents, rooms, `/dev/xp`).
- Schemas (`backend/app/schemas/`): Pydantic models for WebSocket envelopes (`envelopes.py`: INIT, STATE_UPDATE, PONG) and events. Nested entity payloads are deliberately loose (`extra="allow"`) — serialization happens in `engine/game/serialization.py`.
- Persistence: none — all state is in memory; games reset on server restart.

### Frontend (`frontend/`)

- React 19 + Vite, canvas-based rendering (`src/rendering/`), not DOM.
- **The client is a pure renderer + input sender — never put game logic client-side.**
- TypeScript is adopted gradually and is **mixed inside JS directories** (65 `.ts/.tsx` vs 237 `.js/.jsx`); `src/net/` is fully TS, and newer modules elsewhere tend to be TS. Don't assume a directory is single-language.
- Layout under `frontend/src/`: `net/` (WebSocket client `useGameSocket.ts`, `events/` dispatcher, `sync/` state synchronizers, `movement/` prediction), `rendering/`, `game/` (targeting, auto-aim, talents UI), `ui/` (`Wnd*.jsx` names mirror SPD window classes), `menu/`, `handlers/`, `hooks/`, `input/`, `pathfinding/`, `audio/`, `data/`, `dev/`, `locales/` (en, ru — i18next).
- API URL resolution order (`src/config/urls.js`): `window.__APP_CONFIG__.API_URL` → `import.meta.env.VITE_API_URL` → a hardcoded production URL. In Docker the nginx image writes `env.js` from `env.template.js` at container start (`docker-entrypoint.d/30-runtime-env.sh`), so `VITE_API_URL` is a *runtime* value there but a *build-time* value under Vite.

### Shared contract (backend ↔ frontend types)

- The Pydantic models in `backend/app/engine/entities/` (`base.py`, `player.py`) are the single source of truth for shapes crossing the socket.
- `frontend/src/types/generated/entities.ts` is **auto-generated — never edit it manually**. After changing backend entity models run, from `frontend/`:
  - `npm run gen:schema` — dumps JSON Schema via `backend/scripts/export_contract_schema.py` (uses `backend/venv`);
  - `npm run gen:types` — that plus `json-schema-to-typescript` to rewrite `entities.ts`.
- Envelopes and event payloads are assembled as plain dicts server-side and hand-written in `frontend/src/types/contract.ts` — those are *not* generated.

### SPD fidelity workflow

Before implementing or changing a mechanic, trace the exact flow in the upstream Java source (`shattered-pixel-dungeon/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/` — `actors/`, `items/`, `levels/`, `mechanics/`) and consult `docs/spd_*.md` and `docs/spd_items/`. When the port deliberately deviates from SPD, say so.

## Build and run

```bash
docker compose up
```

- Frontend: http://localhost:3000, Backend: http://localhost:8080
- **No hot reload in Docker.** `backend` runs `python app/main.py` (uvicorn, no `--reload`) → `docker compose restart backend` after edits. The `frontend` mount `./frontend:/app` is inert: the image serves a `dist/` baked at build time into `/usr/share/nginx/html`, so frontend source changes need `docker compose up --build frontend`.
- `frontend/Dockerfile` builds with **bun** (`oven/bun:alpine`, `bun.lock`); local dev uses npm with `package-lock.json`. Both lockfiles are committed — keep each tool's lockfile consistent when touching dependencies.
- Env: root `.env` (see `.env.example`) holds `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` for feedback notifications. `main.py` loads root `.env` then `backend/.env`. Backend env vars: `ADMIN_SECRET`, `PUBLIC_ROOM_SEED` (empty = deterministic `crc32(game_id)` fallback), `GAME_LOOP_HZ`, `PORT`.

### Without Docker

```bash
cd backend  && venv/bin/python app/main.py     # :8080, uses backend/venv
cd frontend && npm install && npm run dev      # vite on :3000
```

## Testing

### Backend — pytest, 102 test files in `backend/tests/`

```bash
cd backend && venv/bin/python -m pytest tests/ -q                 # full suite
cd backend && venv/bin/python -m pytest tests/test_spd_random.py -q  # single file
cd backend && venv/bin/python -m pytest tests/ -q -k turn_scheduler # by name
```

- **Use `python -m pytest`, not `venv/bin/pytest`** — there is no `pytest.ini`/`pyproject.toml`, so `app.*` imports only resolve because `-m` puts the cwd on `sys.path`. Bare `venv/bin/pytest` fails with `ModuleNotFoundError: No module named 'app'`. Always run from `backend/`.
- Fixtures in `backend/tests/conftest.py`: `game` (real generated depth-1 floor, mobs cleared) and `open_game_factory(width, height, depth)` (floor cleared to an open all-FLOOR rectangle). Use them for **new** tests; the ~300 existing `GameInstance(...)` call sites intentionally keep their local helpers — don't do a drive-by migration.
- Root `./run_tests.sh` is **stale**: it execs `backend/tests/verify_ranged_combat.py`, which no longer exists. Use pytest.
- No Python linter/formatter is configured — don't add one implicitly; the venv just happens to ship `pyflakes`.

### Frontend — node:test via tsx, plus lint and typecheck

```bash
cd frontend
npm run lint       # eslint flat config; src/types/generated ignored
npm run typecheck  # tsc --noEmit
npm test           # npx tsx --test "src/**/*.test.js"
```

- Verify with `lint` → `typecheck`; add `test` when touching logic that has tests.
- `npm test` glob is `*.test.js` only — a new `.test.ts` would be **silently skipped**. All 27 frontend tests are `.test.js`.
- `npm run lint` currently reports 2 pre-existing `react-hooks/exhaustive-deps` warnings in `src/hooks/renderingHooks.js` and still exits 0. Don't chase those; only new errors matter.
- TS is strict (`strict`, `noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`); `.js/.jsx` are linted but not type-checked (`checkJs: false`). ESLint `no-unused-vars` errors except names matching `^[A-Z_]`.

## Code style guidelines

- Prefer a new mixin/module over growing an existing engine file. (The ≤400-line target isn't enforced — `cleric_spells.py` is 1368 lines, `entities/player.py` 1141 — so don't do drive-by splits.)
- **No code comments unless asked**; match the surrounding style.
- All game tuning constants go in `backend/app/engine/game/constants.py`.
- `backend/app/engine/dungeon/spd_random.py` must stay behaviorally identical to SPD's Java RNG.
- Backend imports use the `app.` package root. Invoke Python tools via `backend/venv/bin/python`.

## Versioning, branches, release

- Version lives in `frontend/package.json` and is the single version for the whole project.
- `core.hooksPath = .githooks` is already configured, so `.githooks/pre-commit` runs automatically: it auto-bumps the version once per branch — `feature/*` → minor (patch reset to 0), `bugfix/*` and `chore/*` → patch, `release/*` → untouched. It bails if you edited the version by hand. Skip with `git commit --no-verify`.
- `.github/workflows/release.yml`: on push to `main`, creates GitHub release `v<version>` with generated notes if the tag doesn't exist.
- Deploy: `./deploy.sh` builds both images, pushes to Docker Hub (`artemnikov/...`), deploys each to **Google Cloud Run** with `--no-traffic` (project `studied-sled-487417-m2`, region `europe-west1`), then routes traffic only after both succeed. `backend/cloudbuild.yaml` / `frontend/cloudbuild.yaml` are legacy.

## Security considerations

- Never commit `.env` (git-ignored). Secrets: `ADMIN_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Admin access is gated by `ADMIN_SECRET`, which defaults to `"admin"` in `main.py:55` and in `docker-compose.yml` — and `deploy.sh` doesn't set it at all in production.
- `POST /dev/xp/{game_id}/{player_id}/{amount}` (`backend/app/api/routes.py:318`) is an **unauthenticated** grant-XP route that ships to production; CORS is `*` by design. Room passwords are checked server-side in `connection_manager.check_room_join` before any game state is created.
- The backend Docker image runs as a non-root user; keep secrets in env vars, not command-line history or logs.
