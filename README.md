# Ecosystem Evolution Simulator

A pygame-based 2D ecosystem where plants, herbivores, and carnivores interact, reproduce, and evolve through trait mutation. Watch lineages diverge in real time via color and size shifts, with kill / eat / birth / death flash effects and a live population graph.

For a deeper architectural breakdown (class hierarchy, evolution model, tuning constants), see `CLAUDE.md`.

---

## Running the simulation

```bash
/usr/bin/python3 ecosystem_sim.py
```

### Why the explicit `/usr/bin/python3` path?

This machine has two Pythons:

- `python3` on the default PATH → `/home/linuxbrew/.linuxbrew/bin/python3` (Homebrew, 3.13). **Does NOT have pygame.**
- `/usr/bin/python3` (system Python, 3.12). **Has pygame** because we installed it via apt.

If you just type `python3 ecosystem_sim.py`, you'll get `ModuleNotFoundError: No module named 'pygame'`. Always use the absolute `/usr/bin/python3` path, or set up a venv (see below).

### Installing pygame (already done, but for reference)

The system-Python install:
```bash
sudo apt install python3-pygame
```

If you want pygame available to your default Homebrew Python instead, use a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pygame
python ecosystem_sim.py
```
With a venv, you'll need `source .venv/bin/activate` each new terminal session.

---

## Keyboard controls

| Key | Action |
|---|---|
| `SPACE` | Pause / resume |
| `R` | Reset to initial population |
| `P` | Spawn 10 plants |
| `H` | Spawn 1 herbivore |
| `C` | Spawn 1 carnivore |
| `ESC` | Quit |

---

## Tuning the simulation

All knobs are constants at the top of `ecosystem_sim.py`. Notable ones:

- `MUTATION_RATE`, `SUPER_MUTATION_CHANCE`, `SUPER_MUTATION_FACTOR` — evolution speed and rare outliers.
- `PLANT_GROWTH_RATE`, `MAX_PLANTS` — food abundance.
- `EXTINCTION_RECOVERY` — auto-reseed when a species dies out (set to `False` if you want to observe extinctions).
- `HERBIVORE_DEFAULTS`, `CARNIVORE_DEFAULTS` — starting traits before mutation drift.
- `TRAIT_BOUNDS` — hard clamps preventing runaway evolution.
- `EFFECT_KILL` / `EFFECT_EAT_PLANT` / `EFFECT_BIRTH` / `EFFECT_DEATH` — `(color, max_radius, duration)` for the four flash types.

---

## What's been built (recap)

Two rounds of improvements layered on the original simulation:

**Round 1 — mechanics:**
- `SpatialGrid` for O(1)-ish nearest-neighbor scans (replaces O(n²)).
- Extinction recovery (auto-reseed on species collapse).
- Trait mutation on reproduction (speed, vision, threshold; clamped to `TRAIT_BOUNDS`).
- Population history graph in the top-right.

**Round 2 — drama:**
- Trait-driven color (HSV-shifted from per-species base hue based on speed and vision).
- Trait-driven radius (scales with `energy_decay`).
- Higher mutation rate (0.20) plus rare ±50% super-mutations.
- Eat / kill / birth / death flash effects (expanding fading rings).
- Tradeoff coupling: `energy_decay` derives from `√(speed × vision)` against species defaults, so fast + wide-vision lineages pay for it with higher metabolism.

---

## Git workflow

### Committing and pushing the current branch

```bash
git add <files>                 # stage specific files (avoid `git add .`)
git commit -m "your message"
git push -u origin <branch>     # `-u` sets upstream so future push/pull need no args
```

### Merging a feature branch into main

**Path A — GitHub PR (recommended, leaves a record):**
1. After `git push -u origin <branch>`, GitHub prints a PR-creation URL — visit it and open the PR.
2. On GitHub, click **Merge pull request**.
3. Locally:
   ```bash
   git checkout main
   git pull
   ```

**Path B — local merge (faster, no PR record):**
```bash
git checkout main
git pull
git merge <branch>
git push
```

### Starting a new branch from main

```bash
git checkout main
git pull                        # make sure main is current
git checkout -b <new-branch>
```

### Optional cleanup after merging

```bash
git branch -d <merged-branch>              # delete local
git push origin --delete <merged-branch>   # delete remote
```

`git branch -d` is safe — it refuses to delete unmerged branches. Use `-D` only if you're certain.

---

## Roadmap: Anthropic SDK Sandbox

The goal is to evolve this into a data-generating simulator that serves as a hands-on sandbox for learning the Anthropic suite of technologies. The sim always runs visually (pygame stays); an optional `--headless N` flag enables silent batch runs for volume data generation.

### Phase 1 — Data Pipeline Foundation
*Make the sim produce exportable, structured data while running normally*

- Add event logging that fires silently in the background while you watch the sim
- Event schema: `{frame, day, type, entity_id, species, x, y, energy, traits}` — covers birth, death, eat_plant, kill, extinction, superpredator_spawn
- On exit, write the run to `runs/run_<timestamp>.json` with a summary (duration, peak populations, trait drift stats)
- Optional `--headless N` CLI flag for batch generation without pygame

### Phase 2 — Backend API
*Replace the `ecosystem-backend` stub with a real service*

- `POST /runs` — ingest a completed run JSON
- `GET /runs` — list stored runs with metadata
- `GET /runs/{id}/events` — full event log
- `GET /runs/{id}/summary` — population stats and trait drift
- SQLite persistence via SQLAlchemy

### Phase 3 — Claude API Integration *(first real Anthropic touchpoint)*

- `POST /runs/{id}/analyze` — sends run summary to Claude, returns a narrative ecological analysis
- Streaming response: text streams in as Claude writes
- Interactive Q&A: ask Claude questions about a specific run using the event log as context
- **Learns:** Anthropic Python SDK, prompt engineering, streaming, context window design

### Phase 4 — Tool Use / Agents

- Define Claude tools: `run_simulation(config)`, `query_events(run_id, filters)`, `compare_runs(id_a, id_b)`
- Agentic loop: Claude autonomously designs and runs experiments ("What mutation rate causes the fastest herbivore extinction?")
- Multi-turn conversation with tool calls persisted across turns
- **Learns:** Tool use, agentic patterns, multi-turn state management

### Phase 5 — React Dashboard
*Wire `ecosystem-sim/` to the real backend*

- Run history list, per-run population graphs, event timeline
- Chat panel for Claude Q&A about any stored run
- Parameter form that triggers a new headless run
- The pygame window remains the live view; React is the analysis layer
- **Learns:** Streaming Claude responses into a UI

### Phase 6 — Advanced Patterns *(later)*

- **Embeddings:** vectorize run summaries, cluster similar ecosystem dynamics
- **Multi-agent:** one agent plans experiments, another critiques the methodology
- **Claude Code hooks:** auto-trigger post-run analysis via `PostToolUse` hooks
