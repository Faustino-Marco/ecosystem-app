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
PLANT_GROWTH_RATE = 75 # Lower is faster
MAX_PLANTS = 150
FRAMES_PER_DAY = 200

# --- Utility Functions ---
def distance(p1, p2):
    """Calculate the distance between two points (x, y tuples)."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

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
        """Draw the creature on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        # Optional: Draw energy bar for mobile creatures
        if hasattr(self, 'max_energy'):
            energy_percentage = self.energy / self.max_energy
            bar_width = self.radius * 2
            bar_height = 5
            bar_x = self.x - self.radius
            bar_y = self.y - self.radius - 10
            
            # Health bar color
            if energy_percentage > 0.5:
                health_color = GREEN
            elif energy_percentage > 0.2:
                health_color = YELLOW
            else:
                health_color = RED

            pygame.draw.rect(screen, (50, 50, 50), (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2))
            pygame.draw.rect(screen, health_color, (bar_x, bar_y, bar_width * energy_percentage, bar_height))

    def move(self):
        """Update the creature's position based on its velocity."""
        self.x += self.vx
        self.y += self.vy

    def handle_boundaries(self):
        """Keep the creature within the screen boundaries."""
        if self.x < self.radius or self.x > SCREEN_WIDTH - self.radius:
            self.vx *= -1
        if self.y < self.radius or self.y > SCREEN_HEIGHT - self.radius:
            self.vy *= -1
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))

    def update(self, entities, add_entity_callback):
        """Update the creature's state for one frame."""
        self.move()
        self.handle_boundaries()
        self.energy -= self.energy_decay
        if self.energy <= 0:
            self.is_alive = False

# --- Species Classes ---
class Plant(Creature):
    """A stationary food source."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.type = 'plant'
        self.radius = 5
        self.color = GREEN
        self.energy = PLANT_ENERGY

    def update(self, entities, add_entity_callback):
        # Plants are stationary and don't lose energy
        pass

class Herbivore(Creature):
    """Eats plants."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.type = 'herbivore'
        self.radius = 8
        self.color = BLUE
        self.speed = 1.2
        self.energy_decay = 0.15
        self.max_energy = 200
        self.energy = 100
        self.vision_radius = 150
        self.reproduction_threshold = 180

    def update(self, entities, add_entity_callback):
        # Find the nearest plant
        nearest_plant = None
        min_dist = float('inf')
        for entity in entities:
            if entity.type == 'plant':
                d = distance((self.x, self.y), (entity.x, entity.y))
                if d < min_dist and d < self.vision_radius:
                    min_dist = d
                    nearest_plant = entity
        
        # Move towards the plant or wander
        if nearest_plant:
            angle = math.atan2(nearest_plant.y - self.y, nearest_plant.x - self.x)
            self.vx = math.cos(angle) * self.speed
            self.vy = math.sin(angle) * self.speed
            # Check for eating
            if min_dist < self.radius + nearest_plant.radius:
                self.energy = min(self.max_energy, self.energy + nearest_plant.energy)
                nearest_plant.is_alive = False
        else:
            if random.random() < 0.05: # Wander
                self.vx = random.uniform(-self.speed, self.speed)
                self.vy = random.uniform(-self.speed, self.speed)

        super().update(entities, add_entity_callback)

        # Reproduction
        if self.energy >= self.reproduction_threshold:
            self.energy /= 2
            add_entity_callback(Herbivore(self.x + random.uniform(-10, 10), self.y + random.uniform(-10, 10)))

class Carnivore(Creature):
    """Eats herbivores."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.type = 'carnivore'
        self.radius = 10
        self.color = RED
        self.speed = 1.5
        self.energy_decay = 0.2
        self.max_energy = 300
        self.energy = 150
        self.vision_radius = 200
        self.reproduction_threshold = 250

    def update(self, entities, add_entity_callback):
        # Find the nearest herbivore
        nearest_prey = None
        min_dist = float('inf')
        for entity in entities:
            if entity.type == 'herbivore':
                d = distance((self.x, self.y), (entity.x, entity.y))
                if d < min_dist and d < self.vision_radius:
                    min_dist = d
                    nearest_prey = entity
        
        # Move towards prey or wander
        if nearest_prey:
            angle = math.atan2(nearest_prey.y - self.y, nearest_prey.x - self.x)
            self.vx = math.cos(angle) * self.speed
            self.vy = math.sin(angle) * self.speed
            # Check for eating
            if min_dist < self.radius + nearest_prey.radius:
                self.energy = min(self.max_energy, self.energy + nearest_prey.energy / 2)
                nearest_prey.is_alive = False
        else:
            if random.random() < 0.05: # Wander
                self.vx = random.uniform(-self.speed, self.speed)
                self.vy = random.uniform(-self.speed, self.speed)

        super().update(entities, add_entity_callback)

        # Reproduction
        if self.energy >= self.reproduction_threshold:
            self.energy /= 2
            add_entity_callback(Carnivore(self.x + random.uniform(-10, 10), self.y + random.uniform(-10, 10)))

# --- Main Simulation Function ---
def main():
    """Main function to run the simulation."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ecosystem Evolution Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, FONT_SIZE)
    
    entities = []
    
    def add_entity(entity):
        entities.append(entity)

    def initial_population():
        entities.clear()
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
        
        # --- Event Handling ---
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

        # --- Update Logic ---
        if not is_paused:
            entities_to_add = []
            def add_entity_callback(entity):
                entities_to_add.append(entity)

            # Update all entities
            for entity in entities:
                entity.update(entities, add_entity_callback)
            
            # Filter out dead entities
            entities = [e for e in entities if e.is_alive]
            # Add newly born entities
            entities.extend(entities_to_add)

            # Natural plant growth
            plant_count = sum(1 for e in entities if e.type == 'plant')
            if frame_count % PLANT_GROWTH_RATE == 0 and plant_count < MAX_PLANTS:
                add_entity(Plant(random.randint(10, SCREEN_WIDTH - 10), random.randint(10, SCREEN_HEIGHT - 10)))
            
            # Update day counter
            frame_count += 1
            if frame_count >= FRAMES_PER_DAY:
                frame_count = 0
                day += 1

        # --- Drawing ---
        screen.fill(BLACK)
        
        for entity in entities:
            entity.draw(screen)

        # --- UI and Stats ---
        counts = {'plant': 0, 'herbivore': 0, 'carnivore': 0}
        for e in entities:
            counts[e.type] += 1
        
        day_text = font.render(f"Day: {day}", True, WHITE)
        plant_text = font.render(f"Plants: {counts['plant']}", True, GREEN)
        herb_text = font.render(f"Herbivores: {counts['herbivore']}", True, BLUE)
        carn_text = font.render(f"Carnivores: {counts['carnivore']}", True, RED)

        screen.blit(day_text, (10, 10))
        screen.blit(plant_text, (10, 10 + FONT_SIZE))
        screen.blit(herb_text, (10, 10 + FONT_SIZE * 2))
        screen.blit(carn_text, (10, 10 + FONT_SIZE * 3))

        if is_paused:
            pause_font = pygame.font.SysFont(None, 60, bold=True)
            pause_text = pause_font.render("PAUSED", True, YELLOW)
            text_rect = pause_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
            screen.blit(pause_text, text_rect)

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
