# Network investigation contract instructions

## Purpose
Maintain the authoritative contract in `README.md` for `src/fintrace/investigations/`. Implementation is pending.

## Inputs
- Account/alert seeds, time interval, direction, hop limit and node/edge display budgets.
- Stored graph evidence, findings and deterministic layout seed.

## Outputs
- Interactive directed neighbourhood, node/edge details and highlighted temporal paths/cycles.
- Layout coordinates, exportable graph data and truncation/filter diagnostics.

## Functionality
- Allow incoming/outgoing expansion and highlight evidence-specific account roles.
- Display amount, currency, timestamp and transaction reference on edge selection.
- Keep actual parallel payments accessible even when the initial view aggregates edges.
- Use NetworkX to prepare graph data, PyVis for interaction and Matplotlib for static exports.

## Maintenance constraints
Keep the proposed interface, data-availability gates, failure modes and acceptance criteria synchronized with implementation. Do not present proposed APIs as implemented. Changes must preserve root instructions, cutoff isolation, source lineage and transparent evidence. Verify the acceptance criteria in README.md when this feature is implemented.
