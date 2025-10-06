from gymnasium.envs.registration import register
from env import GridWorldEnv

register(
    id="GridWorld-v0",
    entry_point=GridWorldEnv,
)
