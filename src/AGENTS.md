# src instructions

## Purpose
Contain installable Python source under the src layout.

## Inputs
Package metadata and implementation modules.

## Outputs
The fintrace package.

## Functionality
Keep domain services under fintrace and shared records in its contracts module. Do not place UI or bulk data here.

## Constraints
Respect deeper folder instructions and module implementation status. Ingestion/source auditing, financial validation and deterministic transaction rules are implemented; temporal graphs and bounded PNG visualization are implemented. Fixed-policy priorities and transactional audited alerts are implemented. Snapshot-scoped investigation models and the core Streamlit UI are implemented. Full-history queries and case services remain pending. Avoid import-time side effects or network requests.
