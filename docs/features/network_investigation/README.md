# Network investigation

**Status: implementation pending.** Owner: `src/fintrace/investigations/`.

## Proposed interface
```text
get_network_view(seeds, time_range, expansion_policy, run_id) -> NetworkView
```
This is a design signature, not an existing callable API. Concrete types must follow `docs/data_contracts.md`.

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

## Errors and edge cases
- Never load an unlimited full benchmark graph into the browser.
- Display truncation does not silently alter underlying evidence or score.
- Seeds outside the selected run/time interval return a clear no-data result.

## Acceptance criteria
- A highlighted cycle corresponds exactly to ordered evidence transactions.
- A 200-node display limit reports omitted scope.
- Repeated identical views use stable layout settings and node identities.

## Data availability
Core feature; interactive and static rendering remain pending.
