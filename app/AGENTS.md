# app instructions

## Purpose
Present Streamlit views over implemented service outputs; the entry point provides the implemented investigation workspace.

## Inputs
Service read models, selected dataset/run, validated filters and explicit analyst actions.

## Outputs
Rendered overview/queue/investigation/case/report/evaluation/replay screens and user action requests.

## Functionality
Keep presentation in this folder. streamlit_app.py routes overview, alert review, account evidence and network explorer. Views call source services, expose evidence, preserve applied filters and display synthetic provenance, cutoff and incomplete coverage.

## Constraints
No detection, scoring, database joins or benchmark labels in ordinary screens. Do not show fabricated counts. Evaluation is a separate view. Implemented capabilities must remain distinct from planned pages.

Default reads are read-only and do not create a store. Only explicit review form submissions call AlertStore.transition with actor/reason/current timestamp and expected version. FINTRACE_ALERT_DATABASE and FINTRACE_PROCESSED_ROOT are operator-controlled local paths. Case, report and replay pages delegate explicit form/button submissions to their domain services; ordinary reads/rerenders create no storage or artifacts. Evaluation stays pending. FINTRACE_EXPORT_ROOT selects the operator-controlled local report directory.

Evidence reference lists render at most 200 IDs with a complete selected-finding JSON download. Downloads do not persist or transmit files externally. CSS/resources are local; Streamlit >=1.66 is required for supported HTML/iframe APIs.

Use the dark operations theme in .streamlit/config.toml and app/style.css, including readable captions, controls, metrics and tables. Embedded PyVis frames have their own matching dark canvas and tooltip styles. Preserve visible warnings, evidence limits and synthetic-data context.
