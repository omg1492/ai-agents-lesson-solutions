import numpy as np
import gymnasium as gym
import matplotlib.pyplot as plt
import setup


def choose_action(state, q_table, epsilon, env):
    """
    Epsilon-greedy action selection.

    With probability ε: explore (random action)
    With probability 1-ε: exploit (best action from Q-table)
    """
    row, col = state

    if np.random.rand() < epsilon:
        return env.action_space.sample()  # Random exploration

    return np.argmax(q_table[row, col])  # Greedy exploitation


def train_q_learning(
    episodes=1000,
    alpha=0.1,
    gamma=0.9,
    epsilon=0.1,
    grid_size=5,
    seed=42
):
    """
    Train Q-learning agent in Grid World.

    Args:
        episodes: Number of training episodes
        alpha: Learning rate
        gamma: Discount factor
        epsilon: Exploration rate
        grid_size: Size of the grid
        seed: Random seed for reproducibility

    Returns:
        Trained Q-table
    """
    # Create environment
    env = gym.make("GridWorld-v0", grid_size=grid_size, num_obstacles=3, seed=seed)

    # Initialize Q-table: (grid_size x grid_size x 4 actions)
    q_table = np.zeros((grid_size, grid_size, 4))

    print("\n" + "=" * 50)
    print("TRAINING Q-LEARNING AGENT")
    print("=" * 50)
    print(f"Episodes: {episodes}")
    print(f"Learning rate (α): {alpha}")
    print(f"Discount factor (γ): {gamma}")
    print(f"Exploration rate (ε): {epsilon}")
    print("=" * 50)

    episode_rewards = []
    episode_lengths = []
    progress_lines = []

    for episode in range(episodes):
        state, _ = env.reset()
        state = (state * (grid_size - 1)).astype(int)  # Denormalize: [0,1] → grid coords

        total_reward = 0
        done = False

        while not done:
            # Choose action
            action = choose_action(state, q_table, epsilon, env)

            # Take action
            next_state, reward, terminated, truncated, _ = env.step(action)
            next_state = (next_state * (grid_size - 1)).astype(int)  # Denormalize: [0,1] → grid coords

            # Q-learning update rule (off-policy)
            # Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]
            row, col = state
            next_row, next_col = next_state

            q_table[row, col, action] += alpha * (
                reward + gamma * np.max(q_table[next_row, next_col, :]) - q_table[row, col, action]
            )

            state = next_state
            total_reward += reward
            done = terminated or truncated

        episode_rewards.append(total_reward)
        episode_lengths.append(env.unwrapped.step_counter)

        if (episode + 1) % 100 == 0:
            avg_reward = np.mean(episode_rewards[-100:])
            avg_length = np.mean(episode_lengths[-100:])
            progress_lines.append(
                f"Episode {episode + 1}/{episodes} | "
                f"Avg Reward: {avg_reward:.2f} | "
                f"Avg Length: {avg_length:.2f}"
            )

    env.close()

    # Print all progress lines at the end
    print()
    for line in progress_lines:
        print(line)

    # Save Q-table
    np.save("q_table.npy", q_table)
    print("\n" + "=" * 50)
    print("✅ Training complete! Q-table saved to 'q_table.npy'")
    print("=" * 50)

    return q_table, episode_rewards, episode_lengths


def plot_results(episode_rewards, episode_lengths):
    """
    Plot training results with moving average.

    Creates two subplots:
    - Left: Episode rewards over time
    - Right: Episode length (steps) over time
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Plot rewards
    axes[0].plot(episode_rewards, alpha=0.3, label='Episode Reward')
    # Moving average smooths the noisy reward signal
    window = 50
    if len(episode_rewards) >= window:
        moving_avg = np.convolve(episode_rewards, np.ones(window) / window, mode='valid')
        axes[0].plot(range(window - 1, len(episode_rewards)), moving_avg,
                     label=f'{window}-Episode Moving Average', linewidth=2)
    axes[0].set_xlabel('Episode')
    axes[0].set_ylabel('Total Reward')
    axes[0].set_title('Training Rewards')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot episode lengths
    axes[1].plot(episode_lengths, alpha=0.3, label='Episode Length')
    if len(episode_lengths) >= window:
        moving_avg = np.convolve(episode_lengths, np.ones(window) / window, mode='valid')
        axes[1].plot(range(window - 1, len(episode_lengths)), moving_avg,
                     label=f'{window}-Episode Moving Average', linewidth=2)
    axes[1].set_xlabel('Episode')
    axes[1].set_ylabel('Steps')
    axes[1].set_title('Episode Length')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('training_results.png', dpi=150, bbox_inches='tight')
    print("\n✅ Training plot saved to 'training_results.png'")
    plt.close()


if __name__ == "__main__":
    q_table, rewards, lengths = train_q_learning(
        episodes=1000,
        alpha=0.1,
        gamma=0.95,
        epsilon=0.1,
        grid_size=5,
        seed=42
    )

    # Plot results
    plot_results(rewards, lengths)
