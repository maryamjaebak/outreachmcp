from __future__ import annotations

import os
import pickle
from pathlib import Path

import numpy as np

from outreach_mcp.scoring import FEATURE_NAMES

BANDIT_PATH = os.environ.get("BANDIT_PATH", "./bandit_state.pkl")
RIDGE_LAMBDA = 1.0
EXPLORATION_VARIANCE = 1.0

OUTCOME_REWARDS = {
    "declined": 0.0,
    "replied": 0.5,
    "meeting": 0.75,
    "sponsored": 1.0,
}


def _dim() -> int:
    return len(FEATURE_NAMES)


def _vector(features: dict[str, float]) -> np.ndarray:
    return np.array([features[name] for name in FEATURE_NAMES], dtype=float)


def _load_state() -> tuple[np.ndarray, np.ndarray]:
    path = Path(BANDIT_PATH)
    if path.exists():
        a, b = pickle.loads(path.read_bytes())
        return a, b
    d = _dim()
    return np.eye(d) * RIDGE_LAMBDA, np.zeros(d)


def _save_state(a: np.ndarray, b: np.ndarray) -> None:
    Path(BANDIT_PATH).write_bytes(pickle.dumps((a, b)))


def has_outcomes() -> bool:
    return Path(BANDIT_PATH).exists()


def update(features: dict[str, float], reward: float) -> None:
    """Record a new observation: counts toward both uncertainty and reward."""
    a, b = _load_state()
    x = _vector(features)
    a = a + np.outer(x, x)
    b = b + reward * x
    _save_state(a, b)


def adjust_reward(features: dict[str, float], old_reward: float, new_reward: float) -> None:
    """Correct an already-recorded observation's reward without re-counting its context.

    Used when an outcome is re-logged for the same lead (e.g. "replied" later
    becomes "sponsored") — the feature vector was already absorbed into the
    uncertainty matrix once; only the reward side needs adjusting.
    """
    a, b = _load_state()
    x = _vector(features)
    b = b + (new_reward - old_reward) * x
    _save_state(a, b)


def sample_score(features: dict[str, float], rng: np.random.Generator | None = None) -> float:
    """Thompson-sample a score for one candidate's feature vector.

    Draws a weight vector from the posterior N(mu, v^2 * A^-1) and returns
    w . x. The randomness is what makes repeated calls sometimes favor
    under-explored regions of feature space instead of always the
    best-known one — this is what should drive rank_leads's explore slots
    once outcomes exist.
    """
    rng = rng or np.random.default_rng()
    a, b = _load_state()
    a_inv = np.linalg.inv(a)
    mu = a_inv @ b
    cov = EXPLORATION_VARIANCE * a_inv
    w = rng.multivariate_normal(mu, cov)
    x = _vector(features)
    return float(w @ x)
