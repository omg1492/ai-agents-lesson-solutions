import numpy as np
import gymnasium as gym
import setup


def evaluate_agent(q_table, num_episodes=5, grid_size=5, seed=42):
    """
    Evaluate trained Q-learning agent.

    Args:
        q_table: Trained Q-table
        num_episodes: Number of evaluation episodes
        grid_size: Size of the grid
        seed: Random seed for reproducibility
    """
    env = gym.make("GridWorld-v0", grid_size=grid_size, num_obstacles=3, seed=seed)

    print("\n" + "=" * 50)
    print("Q-TABLE (State-Action Values)")
    print("=" * 50)
    print(f"Dimensions: ({grid_size} rows × {grid_size} cols × 4 actions)")
    print("Actions: Up=0, Right=1, Down=2, Left=3\n")

    for row in range(grid_size):
        for col in range(grid_size):
            rounded_values = np.round(q_table[row, col, :], 2)
            print(f"State ({row},{col}): {rounded_values}")

    print("=" * 50)

    total_rewards = []

    for episode in range(num_episodes):
        state, _ = env.reset()
        state = (state * (grid_size - 1)).astype(int)  # Denormalize

        total_reward = 0
        done = False

        while not done:
            row, col = state

            # Select best action from Q-table
            action = np.argmax(q_table[row, col, :])

            # Print Q-values for current state
            print(f"\nState ({row},{col})")
            print(f"Q-values: Up={q_table[row, col, 0]:.2f} | "
                  f"Right={q_table[row, col, 1]:.2f} | "
                  f"Down={q_table[row, col, 2]:.2f} | "
                  f"Left={q_table[row, col, 3]:.2f}")

            action_names = ["Up", "Right", "Down", "Left"]
            print(f"Chosen Action: {action_names[action]} ({action})")

            # Take action
            next_state, reward, terminated, truncated, _ = env.step(action)
            next_state = (next_state * (grid_size - 1)).astype(int)

            env.render()

            total_reward += reward
            state = next_state
            done = terminated or truncated

        total_rewards.append(total_reward)
        print(f"\n{'=' * 50}")
        print(f"Episode {episode + 1} finished")
        print(f"Steps: {env.unwrapped.step_counter}")
        print(f"Total Reward: {total_reward:.2f}")
        print(f"{'=' * 50}")

    avg_reward = np.mean(total_rewards)
    print(f"\n{'=' * 50}")
    print("EVALUATION SUMMARY")
    print(f"{'=' * 50}")
    print(f"Episodes evaluated: {num_episodes}")
    print(f"Average reward: {avg_reward:.2f}")
    print(f"{'=' * 50}\n")

    env.close()


if __name__ == "__main__":
    # Load trained Q-table
    try:
        q_table = np.load("q_table.npy")
        print("\n✅ Q-table loaded successfully from 'q_table.npy'")
    except FileNotFoundError:
        print("\n❌ Q-table not found. Please run training.py first!")
        exit(1)

    # Evaluate agent
    evaluate_agent(q_table, num_episodes=3, grid_size=5, seed=42)
