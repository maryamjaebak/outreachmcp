from pathlib import Path

import numpy as np
import pytest

from outreach_mcp import bandit
from outreach_mcp.scoring import FEATURE_NAMES


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bandit, "BANDIT_PATH", str(tmp_path / "bandit.pkl"))


def _features(**overrides: float) -> dict[str, float]:
    base = {name: 0.5 for name in FEATURE_NAMES}
    base.update(overrides)
    return base


def test_has_outcomes_false_before_any_update() -> None:
    assert bandit.has_outcomes() is False


def test_has_outcomes_true_after_update() -> None:
    bandit.update(_features(), reward=1.0)
    assert bandit.has_outcomes() is True


def test_sample_score_returns_a_float_before_any_data() -> None:
    score = bandit.sample_score(_features(), rng=np.random.default_rng(0))
    assert isinstance(score, float)


def test_more_updates_with_high_reward_increase_posterior_mean_in_that_direction() -> None:
    hot_features = _features(event_fit=1.0, propensity=1.0)
    cold_features = _features(event_fit=0.0, propensity=0.0)

    for _ in range(20):
        bandit.update(hot_features, reward=1.0)
        bandit.update(cold_features, reward=0.0)

    # average many samples to see past the sampling noise
    rng = np.random.default_rng(0)
    hot_scores = [bandit.sample_score(hot_features, rng) for _ in range(200)]
    cold_scores = [bandit.sample_score(cold_features, rng) for _ in range(200)]

    assert sum(hot_scores) / len(hot_scores) > sum(cold_scores) / len(cold_scores)


def test_adjust_reward_shifts_posterior_without_double_counting_context() -> None:
    features = _features()
    bandit.update(features, reward=0.0)
    a_after_update, _ = bandit._load_state()

    bandit.adjust_reward(features, old_reward=0.0, new_reward=1.0)
    a_after_adjust, _ = bandit._load_state()

    # adjust_reward must not touch the uncertainty matrix, only the reward
    assert np.allclose(a_after_update, a_after_adjust)
