# Currency Judge

## Goal

Predict the short-term direction of USD/JPY using multiple FX market inputs.

The initial target is:

- prediction horizon: 5 minutes
- target: USD/JPY
- output: UP / DOWN
- later: UP / DOWN / FLAT

## Development principles

- Keep prediction logic independent from the Web UI.
- Store every prediction before the result is known.
- Never overwrite historical prediction inputs.
- Evaluate a prediction only using market data obtained after prediction.
- Avoid look-ahead bias and data leakage.
- Store model/version information with every prediction.
- All timestamps must be timezone-aware.
- Internally use UTC for timestamps.
- Add tests for prediction and evaluation logic.

## Development workflow

- Implement one milestone at a time.
- Run tests after changes.
- Do not introduce unnecessary dependencies.
- Update PLAN.md when architecture or milestones change.
