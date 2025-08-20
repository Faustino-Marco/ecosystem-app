import React, { useState, useEffect, useRef, useCallback } from 'react';

// --- Utility Functions ---
const random = (min, max) => Math.random() * (max - min) + min;
const distance = (x1, y1, x2, y2) => Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));

// --- API Communication ---
const logEventToServer = async (eventType, eventData) => {
  try {
    const payload = {
      type: eventType,
      timestamp: new Date().toISOString(),
      data: eventData
    };

    const response = await fetch('http://localhost:5000/log_event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('API Response:', result); // Optional: log success response
  } catch (error) {
    console.error("Could not log event to server:", error);
  }
};


// --- Base Creature Class (Logic, not a React component) ---
class Creature {
  constructor(x, y) {
    this.id = Math.random();
    this.x = x;
    this.y = y;
    this.vx = random(-1, 1);
    this.vy = random(-1, 1);
    this.energy = 100;
    this.isAlive = true;
  }

  draw(ctx) {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.fill();
    // Energy bar
    if (this.maxEnergy) {
      const energyPercentage = this.energy / this.maxEnergy;
      ctx.fillStyle = 'black';
      ctx.fillRect(this.x - this.radius - 1, this.y - this.radius - 8, this.radius * 2 + 2, 6);
      ctx.fillStyle = energyPercentage > 0.5 ? '#4ade80' : energyPercentage > 0.2 ? '#facc15' : '#f87171';
      ctx.fillRect(this.x - this.radius, this.y - this.radius - 7, (this.radius * 2) * energyPercentage, 4);
    }
  }

  update(canvas) {
    this.move(canvas);
    this.handleBoundaries(canvas);
    this.energy -= this.energyDecay;
    if (this.energy <= 0) {
      this.isAlive = false;
    }
  }

  move() {
    this.x += this.vx;
    this.y += this.vy;
  }

  handleBoundaries(canvas) {
    if (this.x < this.radius || this.x > canvas.width - this.radius) this.vx *= -1;
    if (this.y < this.radius || this.y > canvas.height - this.radius) this.vy *= -1;
    this.x = Math.max(this.radius, Math.min(canvas.width - this.radius, this.x));
    this.y = Math.max(this.radius, Math.min(canvas.height - this.radius, this.y));
  }
}

// --- Species Classes ---
class Plant extends Creature {
  constructor(x, y) {
    super(x, y);
    this.type = 'plant';
    this.radius = 5;
    this.color = '#22c55e';
    this.energy = 50;
  }
  update() { } // Plants don't move or lose energy
}

class Herbivore extends Creature {
  constructor(x, y) {
    super(x, y);
    this.type = 'herbivore';
    this.radius = 8;
    this.color = '#3b82f6';
    this.speed = 1.2;
    this.energyDecay = 0.15;
    this.maxEnergy = 200;
    this.energy = 100;
    this.visionRadius = 150;
    this.reproductionThreshold = 180;
  }

  move(canvas, entities) {
    let nearestPlant = null;
    let minDistance = Infinity;

    for (const entity of entities) {
      if (entity.type === 'plant') {
        const d = distance(this.x, this.y, entity.x, entity.y);
        if (d < minDistance && d < this.visionRadius) {
          minDistance = d;
          nearestPlant = entity;
        }
      }
    }

    if (nearestPlant) {
      const angle = Math.atan2(nearestPlant.y - this.y, nearestPlant.x - this.x);
      this.vx = Math.cos(angle) * this.speed;
      this.vy = Math.sin(angle) * this.speed;
    } else {
      if (Math.random() < 0.05) {
        this.vx = random(-this.speed, this.speed);
        this.vy = random(-this.speed, this.speed);
      }
    }
    super.move();
  }

  update(canvas, entities, addEntity) {
    this.move(canvas, entities);
    this.handleBoundaries(canvas);
    this.energy -= this.energyDecay;
    if (this.energy <= 0) this.isAlive = false;

    for (const entity of entities) {
      if (entity.type === 'plant' && entity.isAlive) {
        if (distance(this.x, this.y, entity.x, entity.y) < this.radius + entity.radius) {
          this.energy = Math.min(this.maxEnergy, this.energy + entity.energy);
          entity.isAlive = false;
          break;
        }
      }
    }

    if (this.energy >= this.reproductionThreshold) {
      this.energy /= 2;
      addEntity(new Herbivore(this.x + random(-10, 10), this.y + random(-10, 10)));
    }
  }
}

class Carnivore extends Creature {
  constructor(x, y) {
    super(x, y);
    this.type = 'carnivore';
    this.radius = 10;
    this.color = '#ef4444';
    this.speed = 1.5;
    this.energyDecay = 0.2;
    this.maxEnergy = 300;
    this.energy = 150;
    this.visionRadius = 200;
    this.reproductionThreshold = 250;
  }

  move(canvas, entities) {
    let nearestPrey = null;
    let minDistance = Infinity;

    for (const entity of entities) {
      if (entity.type === 'herbivore') {
        const d = distance(this.x, this.y, entity.x, entity.y);
        if (d < minDistance && d < this.visionRadius) {
          minDistance = d;
          nearestPrey = entity;
        }
      }
    }

    if (nearestPrey) {
      const angle = Math.atan2(nearestPrey.y - this.y, nearestPrey.x - this.x);
      this.vx = Math.cos(angle) * this.speed;
      this.vy = Math.sin(angle) * this.speed;
    } else {
      if (Math.random() < 0.05) {
        this.vx = random(-this.speed, this.speed);
        this.vy = random(-this.speed, this.speed);
      }
    }
    super.move();
  }

  update(canvas, entities, addEntity) {
    this.move(canvas, entities);
    this.handleBoundaries(canvas);
    this.energy -= this.energyDecay;
    if (this.energy <= 0) this.isAlive = false;

    for (const entity of entities) {
      if (entity.type === 'herbivore' && entity.isAlive) {
        if (distance(this.x, this.y, entity.x, entity.y) < this.radius + entity.radius) {
          this.energy = Math.min(this.maxEnergy, this.energy + entity.energy / 2);
          entity.isAlive = false;
          break;
        }
      }
    }

    if (this.energy >= this.reproductionThreshold) {
      this.energy /= 2;
      addEntity(new Carnivore(this.x + random(-10, 10), this.y + random(-10, 10)));
    }
  }
}


// --- React Components ---

const StatCard = ({ title, count, colorClass }) => (
  <div className={`stat-card ${colorClass} bg-opacity-20 p-2 rounded-lg text-center`}>
    <p className={`text-sm ${colorClass.replace('bg', 'text').replace('-500', '-300')}`}>{title}</p>
    <p className="text-xl font-bold">{count}</p>
  </div>
);

const ControlPanel = ({ counts, day, onAddPlant, onAddHerbivore, onAddCarnivore, onTogglePause, onReset, isPaused }) => (
  <aside className="w-full md:w-80 lg:w-96 bg-gray-800 bg-opacity-50 p-4 md:p-6 overflow-y-auto h-1/3 md:h-full backdrop-blur-sm border-l border-gray-700">
    <div className="flex flex-col h-full">
      <h1 className="text-2xl lg:text-3xl font-bold text-cyan-400 mb-4">Ecosystem Controls</h1>

      <div className="grid grid-cols-3 gap-2 mb-4">
        <StatCard title="Plants" count={counts.plant} colorClass="bg-green-500" />
        <StatCard title="Herbivores" count={counts.herbivore} colorClass="bg-blue-500" />
        <StatCard title="Carnivores" count={counts.carnivore} colorClass="bg-red-500" />
      </div>

      <div className="bg-gray-700 bg-opacity-40 p-3 rounded-lg text-center mb-6">
        <p className="text-sm text-gray-400">Simulation Day</p>
        <p className="text-2xl font-bold">{day}</p>
      </div>

      <div className="space-y-3 mb-6">
        <h2 className="text-lg font-semibold text-gray-300 border-b border-gray-600 pb-2">Add Species</h2>
        <button onClick={onAddPlant} className="w-full bg-green-600 hover:bg-green-500 text-white font-bold py-2 px-4 rounded-lg transition duration-300 shadow-lg shadow-green-600/20">Add 10 Plants (P)</button>
        <button onClick={onAddHerbivore} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded-lg transition duration-300 shadow-lg shadow-blue-600/20">Add Herbivore (H)</button>
        <button onClick={onAddCarnivore} className="w-full bg-red-600 hover:bg-red-500 text-white font-bold py-2 px-4 rounded-lg transition duration-300 shadow-lg shadow-red-600/20">Add Carnivore (C)</button>
      </div>

      <div className="space-y-3 flex-grow">
        <h2 className="text-lg font-semibold text-gray-300 border-b border-gray-600 pb-2">Simulation Controls</h2>
        <div className="flex space-x-2">
          <button onClick={onTogglePause} className={`w-full text-white font-bold py-2 px-4 rounded-lg transition duration-300 ${isPaused ? 'bg-green-600 hover:bg-green-500' : 'bg-yellow-600 hover:bg-yellow-500'}`}>{isPaused ? 'Resume' : 'Pause'} (Space)</button>
          <button onClick={onReset} className="w-full bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-4 rounded-lg transition duration-300">Reset (R)</button>
        </div>
      </div>
      <div className="text-xs text-gray-500 mt-4 text-center">
        <p>Click on the canvas or use hotkeys to add species.</p>
      </div>
    </div>
  </aside>
);

export default function App() {
  const canvasRef = useRef(null);
  const entitiesRef = useRef([]);
  const animationFrameIdRef = useRef(null);
  const frameCountRef = useRef(0);

  const [isPaused, setIsPaused] = useState(false);
  const [day, setDay] = useState(0);
  const [counts, setCounts] = useState({ plant: 0, herbivore: 0, carnivore: 0 });

  const FRAMES_PER_DAY = 200;

  const addEntity = useCallback((entity) => {
    entitiesRef.current.push(entity);
    // --- DATA ENGINEERING: Log the birth event ---
    logEventToServer('CREATURE_BIRTH', {
      species: entity.type,
      x: Math.round(entity.x),
      y: Math.round(entity.y)
    });
  }, []);

  const initialPopulation = useCallback(() => {
    entitiesRef.current = [];
    const canvas = canvasRef.current;
    if (!canvas) return;
    for (let i = 0; i < 30; i++) addEntity(new Plant(random(10, canvas.width - 10), random(10, canvas.height - 10)));
    for (let i = 0; i < 10; i++) addEntity(new Herbivore(random(10, canvas.width - 10), random(10, canvas.height - 10)));
    for (let i = 0; i < 3; i++) addEntity(new Carnivore(random(10, canvas.width - 10), random(10, canvas.height - 10)));
  }, [addEntity]);

  const resetSimulation = useCallback(() => {
    setDay(0);
    frameCountRef.current = 0;
    initialPopulation();
    if (isPaused) setIsPaused(false);
  }, [initialPopulation, isPaused]);

  const gameLoop = useCallback(() => {
    if (isPaused) {
      animationFrameIdRef.current = requestAnimationFrame(gameLoop);
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = 'rgba(26, 32, 44, 0.4)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const entitiesToAdd = [];
    const addEntityCallback = (entity) => entitiesToAdd.push(entity);

    entitiesRef.current.forEach(entity => {
      entity.update(canvas, entitiesRef.current, addEntityCallback);
      entity.draw(ctx);
    });

    entitiesRef.current = entitiesRef.current.filter(e => e.isAlive);
    entitiesRef.current.push(...entitiesToAdd);

    if (frameCountRef.current % 50 === 0 && entitiesRef.current.filter(e => e.type === 'plant').length < 100) {
      addEntity(new Plant(random(10, canvas.width - 10), random(10, canvas.height - 10)));
    }

    frameCountRef.current++;
    if (frameCountRef.current >= FRAMES_PER_DAY) {
      frameCountRef.current = 0;
      setDay(d => d + 1);
    }

    if (frameCountRef.current % 5 === 0) {
      const currentCounts = { plant: 0, herbivore: 0, carnivore: 0 };
      entitiesRef.current.forEach(e => {
        currentCounts[e.type]++;
      });
      setCounts(currentCounts);
    }

    animationFrameIdRef.current = requestAnimationFrame(gameLoop);
  }, [isPaused, addEntity]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const resizeCanvas = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    initialPopulation();
    animationFrameIdRef.current = requestAnimationFrame(gameLoop);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameIdRef.current);
    };
  }, [initialPopulation, gameLoop]);

  const addSpecies = useCallback((type, count = 1) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    for (let i = 0; i < count; i++) {
      const x = random(10, canvas.width - 10);
      const y = random(10, canvas.height - 10);
      if (type === 'plant') addEntity(new Plant(x, y));
      if (type === 'herbivore') addEntity(new Herbivore(x, y));
      if (type === 'carnivore') addEntity(new Carnivore(x, y));
    }
  }, [addEntity]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPaused(p => !p);
      }
      if (e.key.toLowerCase() === 'r') resetSimulation();
      if (e.key.toLowerCase() === 'p') addSpecies('plant', 10);
      if (e.key.toLowerCase() === 'h') addSpecies('herbivore');
      if (e.key.toLowerCase() === 'c') addSpecies('carnivore');
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [resetSimulation, addSpecies]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const speciesToAdd = ['plant', 'herbivore', 'carnivore'][(day % 3)];

    if (speciesToAdd === 'plant') addSpecies('plant', 10);
    else addSpecies(speciesToAdd);
  };

  return (
    <div className="bg-gray-900 text-white flex flex-col md:flex-row h-screen font-sans">
      <main className="flex-grow h-2/3 md:h-full relative">
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{ background: 'radial-gradient(circle, #2a3a4a, #1a202c)', cursor: 'crosshair' }}
          onClick={handleCanvasClick}
        />
        {isPaused && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center text-5xl font-bold text-white">
            PAUSED
          </div>
        )}
      </main>
      <ControlPanel
        counts={counts}
        day={day}
        onAddPlant={() => addSpecies('plant', 10)}
        onAddHerbivore={() => addSpecies('herbivore')}
        onAddCarnivore={() => addSpecies('carnivore')}
        onTogglePause={() => setIsPaused(p => !p)}
        onReset={resetSimulation}
        isPaused={isPaused}
      />
    </div>
  );
}
