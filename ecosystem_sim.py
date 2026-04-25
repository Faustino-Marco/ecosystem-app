import pygame
import random
import math

# --- Constants and Settings ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
FONT_SIZE = 20

# Colors
BLACK = (26, 32, 44)
WHITE = (237, 242, 247)
GREEN = (34, 197, 94)
BLUE = (59, 130, 246)
RED = (239, 68, 68)
YELLOW = (234, 179, 8)
CYAN = (34, 211, 238)
GRAY = (107, 114, 128)

# Simulation settings
PLANT_ENERGY = 50
PLANT_GROWTH_RATE = 75  # Lower is faster
MAX_PLANTS = 150
FRAMES_PER_DAY = 200

# Spatial grid
GRID_CELL_SIZE = 200

# Extinction recovery
EXTINCTION_RECOVERY = True
EXTINCTION_RESPAWN_HERBIVORES = 3
EXTINCTION_RESPAWN_CARNIVORES = 2

# Evolution
MUTATION_RATE = 0.20            # ±20% standard jitter per trait
SUPER_MUTATION_CHANCE = 0.05    # 5% chance per reproduction
SUPER_MUTATION_FACTOR = 0.5     # ±50% jolt on one random trait

# Population graph
HISTORY_MAX = 300
HISTORY_SAMPLE_EVERY = 5

# Visual flash effects: (color, max_radius, duration_frames)
EFFECT_KILL = ((255, 255, 255), 24, 14)
EFFECT_EAT_PLANT = ((34, 197, 94), 14, 10)
EFFECT_BIRTH = ((234, 179, 8), 18, 16)
EFFECT_DEATH = ((239, 68, 68), 20, 14)


# --- Utility Functions ---
def distance(p1, p2):
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def mutate(value, lo, hi, rate=None):
    if rate is None:
        rate = MUTATION_RATE
    return max(lo, min(hi, value * random.uniform(1 - rate, 1 + rate)))


# --- Spatial Grid ---
class SpatialGrid:
    """Uniform grid for O(1)-ish nearest-neighbor queries by type."""
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.cells = {}

    def rebuild(self, entities):
        self.cells.clear()
        cs = self.cell_size
        for e in entities:
            key = (int(e.x) // cs, int(e.y) // cs)
            bucket = self.cells.get(key)
            if bucket is None:
                self.cells[key] = [e]
            else:
                bucket.append(e)

    def nearby(self, x, y, radius, type_filter=None):
        cs = self.cell_size
        cx = int(x) // cs
        cy = int(y) // cs
        reach = int(radius // cs) + 1
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                bucket = self.cells.get((cx + dx, cy + dy))
                if not bucket:
                    continue
                for e in bucket:
                    if not e.is_alive:
                        continue
                    if type_filter is None or e.type == type_filter:
                        yield e


# --- Visual Effects ---
class Effect:
    __slots__ = ('x', 'y', 'color', 'max_radius', 'duration', 'age')

    def __init__(self, x, y, spec):
        self.x = x
        self.y = y
        self.color, self.max_radius, self.duration = spec
        self.age = 0

    def step(self):
        self.age += 1
        return self.age < self.duration

    def draw(self, screen):
        progress = self.age / self.duration
        radius = max(1, int(self.max_radius * progress))
        alpha = max(0, int(255 * (1 - progress)))
        size = radius * 2 + 4
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (size // 2, size // 2), radius, 2)
        screen.blit(surf, (int(self.x) - size // 2, int(self.y) - size // 2))


# --- Base Creature Class ---
class Creature:
    """Base class for all entities in the ecosystem."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        self.is_alive = True
        self.energy = 100

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        if hasattr(self, 'max_energy'):
            energy_percentage = self.energy / self.max_energy
            bar_width = self.radius * 2
            bar_height = 5
            bar_x = self.x - self.radius
            bar_y = self.y - self.radius - 10
            if energy_percentage > 0.5:
                health_color = GREEN
            elif energy_percentage > 0.2:
                health_color = YELLOW
            else:
                health_color = RED
            pygame.draw.rect(screen, (50, 50, 50), (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2))
            pygame.draw.rect(screen, health_color, (bar_x, bar_y, bar_width * energy_percentage, bar_height))

    def move(self):
        self.x += self.vx
        self.y += self.vy

    def handle_boundaries(self):
        if self.x < self.radius or self.x > SCREEN_WIDTH - self.radius:
            self.vx *= -1
        if self.y < self.radius or self.y > SCREEN_HEIGHT - self.radius:
            self.vy *= -1
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))

    def update(self, grid, add_entity_callback, add_effect_callback):
        self.move()
        self.handle_boundaries()
        self.energy -= self.energy_decay
        if self.energy <= 0:
            self.is_alive = False
            add_effect_callback(EFFECT_DEATH, self.x, self.y)


# --- Trait defaults / bounds for mutating species ---
HERBIVORE_DEFAULTS = {
    'speed': 1.2,
    'energy_decay': 0.15,
    'vision_radius': 150,
    'reproduction_threshold': 180,
}

CARNIVORE_DEFAULTS = {
    'speed': 1.5,
    'energy_decay': 0.2,
    'vision_radius': 200,
    'reproduction_threshold': 250,
}

TRAIT_BOUNDS = {
    'speed': (0.3, 5.0),
    'energy_decay': (0.05, 0.5),
    'vision_radius': (50, 300),
    'reproduction_threshold': (100, 400),
}


def mutated_traits(parent_traits, defaults):
    """Mutate speed/vision/threshold independently; derive coupled energy_decay.

    Faster + wider-vision lineages pay for it via higher metabolism. A
    super-mutation roll occasionally applies a ±50% jolt to one trait so wild
    outliers appear from time to time.
    """
    new = {}
    independent = ('speed', 'vision_radius', 'reproduction_threshold')
    super_target = random.choice(independent) if random.random() < SUPER_MUTATION_CHANCE else None

    for k in independent:
        lo, hi = TRAIT_BOUNDS[k]
        rate = SUPER_MUTATION_FACTOR if k == super_target else MUTATION_RATE
        new[k] = mutate(parent_traits[k], lo, hi, rate=rate)

    speed_ratio = new['speed'] / defaults['speed']
    vision_ratio = new['vision_radius'] / defaults['vision_radius']
    coupling = math.sqrt(max(0.05, speed_ratio * vision_ratio))
    decay_jitter = random.uniform(1 - MUTATION_RATE * 0.5, 1 + MUTATION_RATE * 0.5)
    decay_lo, decay_hi = TRAIT_BOUNDS['energy_decay']
    new['energy_decay'] = max(decay_lo, min(decay_hi, defaults['energy_decay'] * coupling * decay_jitter))

    return new


def derive_color(traits, defaults, base_hue, fast_direction):
    """Map traits to an HSV-shifted color so mutation is visible at a glance.

    Speed shifts hue (faster → distinctive direction per species), vision
    saturates the color (wider → more vivid).
    """
    speed_ratio = traits['speed'] / defaults['speed']
    vision_ratio = traits['vision_radius'] / defaults['vision_radius']

    speed_delta = max(-1.0, min(1.0, (speed_ratio - 1) / 1.5))
    hue = (base_hue + speed_delta * 30 * fast_direction) % 360

    saturation = max(50, min(100, 75 + (vision_ratio - 1) * 25))
    value = 92

    c = pygame.Color(0)
    c.hsva = (hue, saturation, value, 100)
    return (c.r, c.g, c.b)


def derive_radius(traits, defaults, base_radius):
    """Higher metabolism → bigger silhouette."""
    decay_ratio = traits['energy_decay'] / defaults['energy_decay']
    delta = (decay_ratio - 1) * 2.5
    return max(4, min(18, int(round(base_radius + delta))))


# --- Species Classes ---
class Plant(Creature):
    """A stationary food source."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.type = 'plant'
        self.radius = 5
        self.color = GREEN
        self.energy = PLANT_ENERGY

    def update(self, grid, add_entity_callback, add_effect_callback):
        pass


class Herbivore(Creature):
    """Eats plants."""
    BASE_HUE = 210
    FAST_HUE_DIRECTION = -1  # faster shifts toward cyan
    BASE_RADIUS = 8

    def __init__(self, x, y, traits=None):
        super().__init__(x, y)
        self.type = 'herbivore'
        self.max_energy = 200
        self.energy = 100
        t = traits if traits is not None else HERBIVORE_DEFAULTS
        self.speed = t['speed']
        self.energy_decay = t['energy_decay']
        self.vision_radius = t['vision_radius']
        self.reproduction_threshold = t['reproduction_threshold']
        self.color = derive_color(self.traits(), HERBIVORE_DEFAULTS, self.BASE_HUE, self.FAST_HUE_DIRECTION)
        self.radius = derive_radius(self.traits(), HERBIVORE_DEFAULTS, self.BASE_RADIUS)

    def traits(self):
        return {
            'speed': self.speed,
            'energy_decay': self.energy_decay,
            'vision_radius': self.vision_radius,
            'reproduction_threshold': self.reproduction_threshold,
        }

    def update(self, grid, add_entity_callback, add_effect_callback):
        nearest_plant = None
        min_dist = float('inf')
        for entity in grid.nearby(self.x, self.y, self.vision_radius, 'plant'):
            d = distance((self.x, self.y), (entity.x, entity.y))
            if d < min_dist and d < self.vision_radius:
                min_dist = d
                nearest_plant = entity

        if nearest_plant:
            angle = math.atan2(nearest_plant.y - self.y, nearest_plant.x - self.x)
            self.vx = math.cos(angle) * self.speed
            self.vy = math.sin(angle) * self.speed
            if min_dist < self.radius + nearest_plant.radius and nearest_plant.is_alive:
                self.energy = min(self.max_energy, self.energy + nearest_plant.energy)
                nearest_plant.is_alive = False
                add_effect_callback(EFFECT_EAT_PLANT, nearest_plant.x, nearest_plant.y)
        else:
            if random.random() < 0.05:
                self.vx = random.uniform(-self.speed, self.speed)
                self.vy = random.uniform(-self.speed, self.speed)

        super().update(grid, add_entity_callback, add_effect_callback)

        if self.energy >= self.reproduction_threshold:
            self.energy /= 2
            add_entity_callback(Herbivore(
                self.x + random.uniform(-10, 10),
                self.y + random.uniform(-10, 10),
                traits=mutated_traits(self.traits(), HERBIVORE_DEFAULTS),
            ))
            add_effect_callback(EFFECT_BIRTH, self.x, self.y)


class Carnivore(Creature):
    """Eats herbivores."""
    BASE_HUE = 0
    FAST_HUE_DIRECTION = 1  # faster shifts toward orange
    BASE_RADIUS = 10

    def __init__(self, x, y, traits=None):
        super().__init__(x, y)
        self.type = 'carnivore'
        self.max_energy = 300
        self.energy = 150
        t = traits if traits is not None else CARNIVORE_DEFAULTS
        self.speed = t['speed']
        self.energy_decay = t['energy_decay']
        self.vision_radius = t['vision_radius']
        self.reproduction_threshold = t['reproduction_threshold']
        self.color = derive_color(self.traits(), CARNIVORE_DEFAULTS, self.BASE_HUE, self.FAST_HUE_DIRECTION)
        self.radius = derive_radius(self.traits(), CARNIVORE_DEFAULTS, self.BASE_RADIUS)

    def traits(self):
        return {
            'speed': self.speed,
            'energy_decay': self.energy_decay,
            'vision_radius': self.vision_radius,
            'reproduction_threshold': self.reproduction_threshold,
        }

    def update(self, grid, add_entity_callback, add_effect_callback):
        nearest_prey = None
        min_dist = float('inf')
        for entity in grid.nearby(self.x, self.y, self.vision_radius, 'herbivore'):
            d = distance((self.x, self.y), (entity.x, entity.y))
            if d < min_dist and d < self.vision_radius:
                min_dist = d
                nearest_prey = entity

        if nearest_prey:
            angle = math.atan2(nearest_prey.y - self.y, nearest_prey.x - self.x)
            self.vx = math.cos(angle) * self.speed
            self.vy = math.sin(angle) * self.speed
            if min_dist < self.radius + nearest_prey.radius and nearest_prey.is_alive:
                self.energy = min(self.max_energy, self.energy + nearest_prey.energy / 2)
                nearest_prey.is_alive = False
                add_effect_callback(EFFECT_KILL, nearest_prey.x, nearest_prey.y)
        else:
            if random.random() < 0.05:
                self.vx = random.uniform(-self.speed, self.speed)
                self.vy = random.uniform(-self.speed, self.speed)

        super().update(grid, add_entity_callback, add_effect_callback)

        if self.energy >= self.reproduction_threshold:
            self.energy /= 2
            add_entity_callback(Carnivore(
                self.x + random.uniform(-10, 10),
                self.y + random.uniform(-10, 10),
                traits=mutated_traits(self.traits(), CARNIVORE_DEFAULTS),
            ))
            add_effect_callback(EFFECT_BIRTH, self.x, self.y)


# --- Population Graph ---
def draw_population_graph(screen, font, history):
    graph_w, graph_h = 300, 100
    graph_x = SCREEN_WIDTH - graph_w - 10
    graph_y = 10

    pygame.draw.rect(screen, (40, 46, 60), (graph_x, graph_y, graph_w, graph_h))
    pygame.draw.rect(screen, GRAY, (graph_x, graph_y, graph_w, graph_h), 1)

    max_val = 1
    for series in history.values():
        if series:
            m = max(series)
            if m > max_val:
                max_val = m

    step = graph_w / max(1, HISTORY_MAX - 1)
    for species, color in [('plant', GREEN), ('herbivore', BLUE), ('carnivore', RED)]:
        series = history[species]
        if len(series) < 2:
            continue
        points = []
        for i, v in enumerate(series):
            px = graph_x + int(i * step)
            py = graph_y + graph_h - int(v * graph_h / max_val)
            points.append((px, py))
        pygame.draw.lines(screen, color, False, points, 2)

    label = font.render(f"Population (peak={max_val})", True, WHITE)
    screen.blit(label, (graph_x, graph_y + graph_h + 2))


# --- Main Simulation Function ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ecosystem Evolution Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, FONT_SIZE)

    entities = []
    effects = []
    grid = SpatialGrid(GRID_CELL_SIZE)
    history = {'plant': [], 'herbivore': [], 'carnivore': []}

    def add_entity(entity):
        entities.append(entity)

    def initial_population():
        entities.clear()
        effects.clear()
        for k in history:
            history[k].clear()
        for _ in range(30): add_entity(Plant(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))
        for _ in range(10): add_entity(Herbivore(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))
        for _ in range(3): add_entity(Carnivore(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))

    initial_population()

    running = True
    is_paused = False
    frame_count = 0
    day = 0

    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    is_paused = not is_paused
                if event.key == pygame.K_r:
                    initial_population()
                    day = 0
                    frame_count = 0
                if event.key == pygame.K_p:
                    for _ in range(10):
                        add_entity(Plant(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))
                if event.key == pygame.K_h:
                    add_entity(Herbivore(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))
                if event.key == pygame.K_c:
                    add_entity(Carnivore(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))

        if not is_paused:
            entities_to_add = []

            def add_entity_callback(entity):
                entities_to_add.append(entity)

            def add_effect_callback(spec, x, y):
                effects.append(Effect(x, y, spec))

            grid.rebuild(entities)

            for entity in entities:
                entity.update(grid, add_entity_callback, add_effect_callback)

            entities = [e for e in entities if e.is_alive]
            entities.extend(entities_to_add)

            plant_count = sum(1 for e in entities if e.type == 'plant')
            if frame_count % PLANT_GROWTH_RATE == 0 and plant_count < MAX_PLANTS:
                add_entity(Plant(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))

            if EXTINCTION_RECOVERY:
                herb_count = sum(1 for e in entities if e.type == 'herbivore')
                carn_count = sum(1 for e in entities if e.type == 'carnivore')
                if herb_count == 0:
                    for _ in range(EXTINCTION_RESPAWN_HERBIVORES):
                        add_entity(Herbivore(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))
                if carn_count == 0:
                    for _ in range(EXTINCTION_RESPAWN_CARNIVORES):
                        add_entity(Carnivore(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))

            effects = [e for e in effects if e.step()]

            frame_count += 1
            if frame_count >= FRAMES_PER_DAY:
                frame_count = 0
                day += 1

        screen.fill(BLACK)

        for entity in entities:
            entity.draw(screen)

        for effect in effects:
            effect.draw(screen)

        counts = {'plant': 0, 'herbivore': 0, 'carnivore': 0}
        for e in entities:
            counts[e.type] += 1

        if not is_paused and frame_count % HISTORY_SAMPLE_EVERY == 0:
            for k in history:
                history[k].append(counts[k])
                if len(history[k]) > HISTORY_MAX:
                    history[k].pop(0)

        day_text = font.render(f"Day: {day}", True, WHITE)
        plant_text = font.render(f"Plants: {counts['plant']}", True, GREEN)
        herb_text = font.render(f"Herbivores: {counts['herbivore']}", True, BLUE)
        carn_text = font.render(f"Carnivores: {counts['carnivore']}", True, RED)

        screen.blit(day_text, (10, 10))
        screen.blit(plant_text, (10, 10 + FONT_SIZE))
        screen.blit(herb_text, (10, 10 + FONT_SIZE * 2))
        screen.blit(carn_text, (10, 10 + FONT_SIZE * 3))

        draw_population_graph(screen, font, history)

        if is_paused:
            pause_font = pygame.font.SysFont(None, 60, bold=True)
            pause_text = pause_font.render("PAUSED", True, YELLOW)
            text_rect = pause_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            screen.blit(pause_text, text_rect)

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
