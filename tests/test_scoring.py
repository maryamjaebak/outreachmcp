from outreach_mcp.scoring import compute_score, load_config

CONFIG = load_config()


def _score(**overrides: object) -> tuple[float, dict[str, float]]:
    defaults: dict[str, object] = {
        "event_fit": 5.0,
        "propensity": 0.8,
        "propensity_signal": True,
        "warm_connection": True,
        "contact_type": "named",
        "email_verified": True,
        "geography": "london",
        "ask_realism": 5.0,
        "n_channels": 3,
        "dnc": False,
        "config": CONFIG,
    }
    defaults.update(overrides)
    result = compute_score(**defaults)  # type: ignore[arg-type]
    return result.total, result.features


def test_best_case_lead_scores_at_scale_max() -> None:
    total, _ = _score(propensity=1.0)
    assert total == CONFIG.score_scale  # every normalized feature is 1.0


def test_dnc_forces_zero_score() -> None:
    total, features = _score(dnc=True)
    assert total == 0.0
    assert features == {}


def test_propensity_without_signal_uses_baseline_not_claimed_value() -> None:
    _, features = _score(propensity=0.99, propensity_signal=False)
    assert features["propensity"] == CONFIG.propensity_baseline_no_signal


def test_propensity_with_signal_uses_claimed_value() -> None:
    _, features = _score(propensity=0.6, propensity_signal=True)
    assert features["propensity"] == 0.6


def test_named_contact_with_unverified_email_is_downgraded() -> None:
    _, features = _score(contact_type="named", email_verified=False)
    assert features["contact_quality"] == CONFIG.contact_quality["unverified_email_downgrade_to"]


def test_named_contact_with_verified_email_keeps_full_score() -> None:
    _, features = _score(contact_type="named", email_verified=True)
    assert features["contact_quality"] == CONFIG.contact_quality["named"]


def test_inbox_contact_quality_unaffected_by_email_verification() -> None:
    _, features = _score(contact_type="inbox", email_verified=False)
    assert features["contact_quality"] == CONFIG.contact_quality["inbox"]


def test_n_channels_caps_at_one() -> None:
    _, features = _score(n_channels=100)
    assert features["n_channels"] == 1.0


def test_geography_maps_to_configured_value() -> None:
    _, features = _score(geography="intl")
    assert features["geography"] == CONFIG.geography["intl"]
