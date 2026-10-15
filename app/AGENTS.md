# app instructions

## Purpose
Present Streamlit views over implemented service outputs; current entry point shows scaffold status only.

## Inputs
Service read models, selected dataset/run, validated filters and explicit analyst actions.

## Outputs
Rendered overview/queue/investigation/case/report/evaluation/replay screens and user action requests.

## Functionality
Keep presentation in this folder. streamlit_app.py is currently a status page. Future views must call source services, expose evidence, preserve applied filters and display synthetic provenance, cutoff and incomplete coverage.

## Constraints
No detection, scoring, database joins or benchmark labels in ordinary screens. Do not show fabricated counts. Evaluation is a separate view. Implemented capabilities must remain distinct from planned pages.
