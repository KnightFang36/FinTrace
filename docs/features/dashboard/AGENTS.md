# Streamlit investigation dashboard contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `app/`. Implementation is pending.

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

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
