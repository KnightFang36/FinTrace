# app/views instructions

## Purpose
Render implemented overview, alert review, account evidence and network pages without exposing placeholder routes.

## Inputs
View-specific service outputs and session filters.

## Outputs
Rendered implemented page content and validated action requests.

## Functionality
Overview summarizes completed runs; alerts filters review work; accounts and networks drill into evidence; cases records explicit actions; evaluation displays frozen benchmark measurements; replay displays progress.

## Constraints
overview.py, alerts.py, account.py and network.py are implemented; cases/evaluation/replay remain unrouted placeholders. Route views from the main app only after the corresponding services exist. Escape untrusted content and avoid duplicate writes on rerender.
