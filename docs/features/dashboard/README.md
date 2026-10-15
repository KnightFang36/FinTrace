# Streamlit investigation dashboard

**Status: implementation pending.** Owner: `app/`.

## Proposed interface
```text
render_dashboard(service_read_models, session_filters) -> StreamlitViews
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

## Inputs
- Implemented service read models and explicit dataset/run selection.
- User filters and validated analyst actions.

## Outputs
- Overview, alert queue, account/network investigation, cases, exports, evaluation and replay views.
- Clear unavailable/pending states and references to source evidence.

## Functionality
- Keep financial calculations and detection logic in source services.
- Label the data as synthetic; show analysis cutoff, policy identity and coverage.
- Provide date/currency/rule/priority/status filters and drill-through evidence.
- Keep benchmark evaluation results in a separate view; do not reveal ground truth in normal investigation pages.
- The current entry point displays a scaffold status page only; planned pages must not fabricate results.

## Errors and edge cases
- Missing datasets/services show actionable pending status, not invented metrics.
- Large graphs use bounded views with visible truncation.
- Case writes require explicit user actions; refreshes must not duplicate actions.

## Acceptance criteria
- Displayed totals and scores come directly from service outputs.
- An unavailable historical rule is not displayed as zero suspicious activity.
- No feature is presented as operational before the underlying service is implemented.

## Data availability
Only the scaffold status page is currently runnable.
