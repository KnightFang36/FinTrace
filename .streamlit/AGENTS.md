# Streamlit runtime configuration

## Purpose
Own the local dashboard theme and runtime defaults.

## Inputs
Versioned UI configuration, never analyst or dataset secrets.

## Outputs
Consistent dark investigation theme and disabled usage telemetry for the local application.

## Functionality
config.toml configures Streamlit presentation. app/ owns page rendering; src/ owns service logic.

## Constraints
Do not commit secrets.toml or credentials. No automatic deployment or public hosting. Keep UI colours accessible and avoid remote asset dependencies.
