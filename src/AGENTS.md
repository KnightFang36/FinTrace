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
Respect deeper folder instructions. The current files are planned service placeholders. Avoid import-time side effects or network requests.
