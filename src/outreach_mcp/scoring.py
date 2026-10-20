from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = os.environ.get("CONFIG_PATH", "./config/config.yaml")


@dataclass(frozen=True)
class ScoringConfig:
    weights: dict[str, float]
    contact_quality: dict[str, float]
    geography: dict[str, float]
    propensity_baseline_no_signal: float
    n_channels_cap: float
    score_scale: float


def load_config(path: str | Path | None = None) -> ScoringConfig:
    with open(path or CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    return ScoringConfig(
        weights=raw["weights"],
        contact_quality=raw["contact_quality"],
        geography=raw["geography"],
        propensity_baseline_no_signal=raw["propensity_baseline_no_signal"],
        n_channels_cap=raw["n_channels_cap"],
        score_scale=raw["score_scale"],
    )


@dataclass(frozen=True)
class ScoreResult:
    total: float
    features: dict[str, float]


def compute_score(
    *,
    event_fit: float,
    propensity: float,
    propensity_signal: bool,
    warm_connection: bool,
    contact_type: str,
    email_verified: bool,
    geography: str,
    ask_realism: float,
    n_channels: int,
    dnc: bool,
    config: ScoringConfig,
) -> ScoreResult:
    """Blend lead features into a single 0-`score_scale` score.

    `propensity` is only trusted when `propensity_signal` is True (i.e. it's
    backed by actual evidence); otherwise it's overridden with the config's
    no-signal baseline, regardless of what was passed in. A "named" contact
    whose email didn't verify is downgraded, since an unverifiable "named"
    contact isn't worth as much as a real one. `dnc` zeroes the score outright.
    """
    if dnc:
        return ScoreResult(total=0.0, features={})

    contact_quality_norm = config.contact_quality[contact_type]
    if contact_type == "named" and not email_verified:
        contact_quality_norm = config.contact_quality["unverified_email_downgrade_to"]

    features = {
        "event_fit": event_fit / 5.0,
        "propensity": propensity if propensity_signal else config.propensity_baseline_no_signal,
        "warm_connection": 1.0 if warm_connection else 0.0,
        "contact_quality": contact_quality_norm,
        "geography": config.geography[geography],
        "ask_realism": ask_realism / 5.0,
        "n_channels": min(n_channels / config.n_channels_cap, 1.0),
    }

    weighted_sum = sum(features[name] * config.weights[name] for name in features)
    return ScoreResult(total=weighted_sum * config.score_scale, features=features)
