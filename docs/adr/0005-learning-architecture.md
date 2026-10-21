# ADR-0005: Logistic regression + linear Thompson sampling, not deep learning

## Context
The design calls for two learned components: a preference model (approve/skip → score blend)
and a contextual bandit (driving explore slots from outcomes). Both operate on the same small,
fixed 7-dimensional feature vector (`scoring.FEATURE_NAMES`) that `save_lead` already computes —
not raw text or embeddings.

## Decision
- Preference model: `sklearn.linear_model.LogisticRegression(C=0.5)`, retrained from scratch on
  every call once 40+ approve/skip decisions exist, persisted as a pickled model file.
- Bandit: linear Thompson sampling via hand-rolled Bayesian ridge regression (NumPy only — no
  bandit library), persisted as a pickled `(A, b)` state tuple.

## Alternatives considered
- A neural network or gradient-boosted model: unjustified complexity for 7 features and (at
  launch) zero training data; also contradicts the project's "no GPU, near-zero cost" framing
  carried over from this author's other projects.
- An existing contextual-bandit library (e.g. Vowpal Wabbit bindings): adds a dependency for an
  algorithm that's about 15 lines of NumPy at this feature-vector size.

## Consequences
Both models are simple enough to retrain/update on every call rather than needing an
incremental-update story — acceptable at this data scale, would need revisiting if decision/
outcome volume grows into the thousands. The reward mapping used by the bandit
(`bandit.OUTCOME_REWARDS`: declined=0.0, replied=0.5, meeting=0.75, sponsored=1.0) is a judgment
call, not something the design doc specified exactly (it only said "reward = reply/sponsor") —
worth the project owner revisiting if the funnel doesn't match reality.
