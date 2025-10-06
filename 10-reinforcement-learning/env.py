import gymnasium as gym
from gymnasium import spaces
import numpy as np


class GridWorldEnv(gym.Env):
    """
    Grid World environment using Gymnasium API.

    Agent navigates from start (0,0) to goal (grid_size-1, grid_size-1)
    avoiding obstacles.
    """

    metadata = {"render_modes": ["human"], "render_fps": 4}

    def __init__(self, grid_size=5, num_obstacles=3, seed=None):
        super().__init__()

        self.grid_size = grid_size
        self.num_obstacles = num_obstacles
        self.rng = np.random.default_rng(seed)

        # Actions: 0=up, 1=right, 2=down, 3=left
        self.action_space = spaces.Discrete(4)

        # Observations: current position (row, col) normalized to [0, 1]
        self.observation_space = spaces.Box(
            low=0,
            high=1,
            shape=(2,),
            dtype=np.float32
        )

        # Environment setup
        self.start_pos = np.array([0, 0], dtype=np.int32)
        self.goal_pos = np.array([grid_size - 1, grid_size - 1], dtype=np.int32)
        self.obstacles = self._generate_obstacles()

        # Episode tracking
        self.state = None
        self.episode_counter = 0
        self.step_counter = 0
        self.max_steps = 100

        print("=" * 50)
        print("GRID WORLD ENVIRONMENT")
        print("=" * 50)
        print(f"Grid size: {self.grid_size}x{self.grid_size}")
        print(f"Start: {tuple(int(x) for x in self.start_pos)}")
        print(f"Goal: {tuple(int(x) for x in self.goal_pos)}")
        print(f"Obstacles: {[tuple(int(x) for x in obs) for obs in self.obstacles]}")
        print("\nACTION SPACE")
        print("0=up, 1=right, 2=down, 3=left")
        print("=" * 50)

    def _generate_obstacles(self):
        """Generate random obstacles avoiding start and goal."""
        obstacles = []
        while len(obstacles) < self.num_obstacles:
            pos = np.array([
                self.rng.integers(0, self.grid_size),
                self.rng.integers(0, self.grid_size)
            ], dtype=np.int32)

            if not (np.array_equal(pos, self.start_pos) or
                    np.array_equal(pos, self.goal_pos) or
                    any(np.array_equal(pos, obs) for obs in obstacles)):
                obstacles.append(pos)

        return obstacles

    def _normalize_state(self, state):
        """
        Normalize state to [0, 1] range.

        Converts grid coordinates to normalized values for observation space.
        """
        return state.astype(np.float32) / (self.grid_size - 1)

    def _denormalize_state(self, normalized_state):
        """
        Convert normalized state back to grid coordinates.

        Used internally to convert observations back to grid indices.
        """
        return (normalized_state * (self.grid_size - 1)).astype(np.int32)

    def reset(self, seed=None, options=None):
        """
        Reset environment to initial state.

        Returns:
            observation: Normalized (row, col) position
            info: Additional information (empty dict)
        """
        super().reset(seed=seed)

        self.episode_counter += 1
        self.step_counter = 0
        self.state = self.start_pos.copy()

        print("\n" + "=" * 50)
        print(f"🌟 Episode {self.episode_counter} - START")
        print("=" * 50)
        print(f"Initial position: {tuple(int(x) for x in self.state)}")
        print(f"Goal position: {tuple(int(x) for x in self.goal_pos)}")
        self.render()

        return self._normalize_state(self.state), {}

    def step(self, action):
        """
        Execute action and return next state, reward, done flags.

        Args:
            action: 0=up, 1=right, 2=down, 3=left

        Returns:
            observation: Normalized next state
            reward: Reward received
            terminated: Whether episode ended naturally (goal reached)
            truncated: Whether episode was cut off (timeout)
            info: Additional information (empty dict)
        """
        self.step_counter += 1

        # Calculate new position
        action_effects = [
            np.array([-1, 0]),  # up
            np.array([0, 1]),   # right
            np.array([1, 0]),   # down
            np.array([0, -1])   # left
        ]

        new_state = self.state + action_effects[action]
        new_state = np.clip(new_state, 0, self.grid_size - 1)

        # Check for obstacles
        hit_obstacle = any(np.array_equal(new_state, obs) for obs in self.obstacles)

        if hit_obstacle:
            reward = -10.0
            terminated = False
            truncated = False
            action_text = ["up", "right", "down", "left"][action]
            print(f"Step {self.step_counter}: Action={action_text}, Hit obstacle! Reward={reward}")
        elif np.array_equal(new_state, self.goal_pos):
            self.state = new_state
            reward = 100.0
            terminated = True
            truncated = False
            action_text = ["up", "right", "down", "left"][action]
            print(f"Step {self.step_counter}: Action={action_text}, State={tuple(int(x) for x in self.state)}")
            print(f"✅ Goal reached in {self.step_counter} steps! Reward={reward}")
        elif self.step_counter >= self.max_steps:
            self.state = new_state
            reward = -1.0
            terminated = False
            truncated = True
            action_text = ["up", "right", "down", "left"][action]
            print(f"Step {self.step_counter}: Action={action_text}, State={tuple(int(x) for x in self.state)}")
            print(f"❌ Max steps ({self.max_steps}) reached. Reward={reward}")
        else:
            self.state = new_state
            reward = -0.1
            terminated = False
            truncated = False
            action_text = ["up", "right", "down", "left"][action]
            print(f"Step {self.step_counter}: Action={action_text}, State={tuple(int(x) for x in self.state)}, Reward={reward}")

        return self._normalize_state(self.state), reward, terminated, truncated, {}

    def render(self):
        """
        Render the grid environment to console.

        Legend:
        - A: Agent position
        - G: Goal position
        - X: Obstacle
        - .: Empty cell
        """
        grid = np.full((self.grid_size, self.grid_size), '.', dtype=str)

        # Mark obstacles
        for obs in self.obstacles:
            grid[tuple(obs)] = 'X'

        # Mark goal
        grid[tuple(self.goal_pos)] = 'G'

        # Mark agent
        grid[tuple(self.state)] = 'A'

        print()
        for row in grid:
            print(' '.join(row))
        print()

    def close(self):
        """Cleanup resources."""
        pass
