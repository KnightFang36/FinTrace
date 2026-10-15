# app/components instructions

## Purpose
Own reusable presentation helpers for tables, filters, graphs and coverage indicators.

## Inputs
Precomputed read models, display limits and selected filters.

## Outputs
Streamlit widgets, bounded graph renderings and safe downloadable artifacts.

## Functionality
Provide implemented shared account-key labels, currency-specific amount formatting, evidence links, severity badges, graph panels and unavailable/partial-state indicators.

## Constraints
Never recalculate financial rules or priorities. Render no unbounded graphs. Display truncation and approximation details.

network.py renders source-bounded data with inline PyVis resources, hashed IDs and escaped labels/tooltips. Never interpolate dataset strings into HTML/CSS or expose remote script sources. coverage.py displays per-service coverage without reclassifying unavailable analysis as zero findings.
