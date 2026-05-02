# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the simulation

```bash
python ecosystem_sim.py
```

Requires `pygame` (`pip install pygame`).

## Architecture

The entire simulation lives in `ecosystem_sim.py`. There is no build step, no test suite, and no package manifest.

**Class hierarchy:**
- `Creature` — base class; handles movement, boundary collision, energy decay, and drawing (including energy bars for mobile entities).
- `Plant(Creature)` — stationary; never loses energy; consumed by herbivores.
- `PoisonPlant(Creature)` — stationary; inert to all species except `Superpredator`, which it kills on contact. Appears only after the overpopulated species drops below `SUPERPREDATOR_RECOVERY`. Pulses purple as a visual warning.
- `Herbivore(Creature)` — seeks nearest plant within `vision_radius`; reproduces by splitting energy when above `reproduction_threshold`. Accepts an optional `traits` dict so offspring can inherit mutated parent traits.
- `Carnivore(Creature)` — seeks nearest herbivore within `vision_radius`; same reproduction and trait-inheritance pattern.
- `Superpredator(Creature)` — spawned automatically when herbivores or carnivores exceed `SUPERPREDATOR_TRIGGER`. Omnivorous (hunts herbivores and carnivores; eats regular plants as fallback). Cannot reproduce. Attracted to `PoisonPlant` (doesn't distinguish it from regular plants) — contact kills it. Eliminated only by poison.
- `SpatialGrid` — uniform grid rebuilt each frame; `nearby(x, y, radius, type_filter)` yields candidate entities so target scans avoid the full O(n²) sweep.
- `Effect` — short-lived expanding ring used for visual feedback on kill / eat / birth / death events. Lives in a parallel `effects` list managed by the main loop.

**Evolution model:** Herbivore and Carnivore expose `traits()` (speed, energy_decay, vision_radius, reproduction_threshold). On reproduction, `mutated_traits()`:
- Jitters `speed`, `vision_radius`, and `reproduction_threshold` independently by ±`MUTATION_RATE`.
- Rolls a `SUPER_MUTATION_CHANCE` chance to apply a ±`SUPER_MUTATION_FACTOR` jolt to one of those three traits, producing wild outliers.
- *Derives* `energy_decay` from the parent's `speed` and `vision_radius` ratios (a √(speed·vision) coupling against species defaults) plus a small jitter — so faster + wider-vision lineages pay for it with higher metabolism. Decay is **not** independently inheritable; it always tracks the coupled value.

**Visual feedback:** Each Herbivore/Carnivore derives its `color` (HSV-shifted from a per-species base hue based on speed and vision) and `radius` (scaled from the coupled `energy_decay`) at construction time. This makes lineage drift legible at a glance: fast/wide-vision creatures shift hue and grow visibly; slow/narrow-vision creatures shrink and dull.

**Main loop (`main()`):**
1. Event handling — keyboard shortcuts mutate `entities` or toggle `is_paused`.
2. `grid.rebuild(entities)` before the update pass.
3. Update phase — each entity's `update(grid, add_entity_callback, add_effect_callback)` is called; new entities and effects are buffered to avoid modifying lists mid-iteration.
4. Dead entities are filtered (`is_alive = False`) after every frame.
5. Natural plant regrowth fires every `PLANT_GROWTH_RATE` frames up to `MAX_PLANTS`.
6. Extinction recovery — if `EXTINCTION_RECOVERY` is on and herbivores/carnivores have hit zero *and no superpredator is active*, reseed a small population to keep the simulation going.
7. Superpredator population control — if herbivores or carnivores breach `SUPERPREDATOR_TRIGGER` and no superpredator is present, one is spawned and a 240-frame warning banner is shown. Once the overpopulated species drops to `SUPERPREDATOR_RECOVERY`, `PoisonPlant` entities begin spawning every `POISON_PLANT_SPAWN_RATE` frames (up to `MAX_POISON_PLANTS`) to eventually eliminate the superpredator.
8. Effects are aged and expired effects are dropped.
9. Draw phase — entities, then effects on top, then HUD stats, then the population history graph in the top-right.

**Population history:** `history` buffers up to `HISTORY_MAX` samples per species, taken every `HISTORY_SAMPLE_EVERY` frames. `draw_population_graph()` renders the series scaled to the current peak.

**Tuning knobs** (top of file):
| Constant | Effect |
|---|---|
| `PLANT_GROWTH_RATE` | Lower = faster plant regrowth |
| `MAX_PLANTS` | Cap on simultaneous plants |
| `FRAMES_PER_DAY` | Speed of the day counter |
| `GRID_CELL_SIZE` | Spatial grid cell size; keep ≥ max expected vision radius |
| `MUTATION_RATE` | Per-trait jitter applied on reproduction |
| `SUPER_MUTATION_CHANCE`, `SUPER_MUTATION_FACTOR` | Probability and magnitude of rare ±50% trait jolts |
| `TRAIT_BOUNDS` | Hard clamps preventing runaway trait drift |
| `EFFECT_KILL` / `EFFECT_EAT_PLANT` / `EFFECT_BIRTH` / `EFFECT_DEATH` / `EFFECT_POISON` | `(color, max_radius, duration)` tuples for the five flash types |
| `EXTINCTION_RECOVERY`, `EXTINCTION_RESPAWN_*` | Toggle and size of reseed populations (suppressed while a superpredator is active) |
| `SUPERPREDATOR_TRIGGER` | Per-species population ceiling before a superpredator spawns |
| `SUPERPREDATOR_RECOVERY` | Triggered-species count at which poison plants start appearing |
| `POISON_PLANT_SPAWN_RATE`, `MAX_POISON_PLANTS` | Cadence and cap for poison plant generation |
| `HISTORY_MAX`, `HISTORY_SAMPLE_EVERY` | Graph window size and sampling cadence |
| Per-class defaults in `HERBIVORE_DEFAULTS` / `CARNIVORE_DEFAULTS` | Starting traits for hand-spawned entities |

## Keyboard controls

| Key | Action |
|---|---|
| `SPACE` | Pause / resume |
| `R` | Reset to initial population |
| `P` | Spawn 10 plants |
| `H` | Spawn 1 herbivore |
| `C` | Spawn 1 carnivore |
| `ESC` | Quit |
