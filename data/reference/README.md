# Optional reference data

Inputs may include independently verified customer identities, expected-activity policies, account/entity links, source channel mappings, and dated external reference lists. Outputs are versioned snapshots with field availability and provenance. No such data is supplied by the IBM transaction export or this repository.

Every future table needs a source identity, acquisition/source terms, effective interval, observed-at timestamp and declared join keys. Identity links use structured bank/account keys. Names, devices, IPs, income, opening dates, countries and ownership must never be fabricated from opaque account IDs.

Maintain explicit unavailable states when data is absent. A shared IP is a link for review, not proof of shared control. Reference intelligence must be independent of IBM laundering labels, and future-known records must not affect historical analysis.

This is a documented extension, not an implemented enrichment or screening pipeline. Reference files remain local and ignored. See [context contract](../../docs/features/entity_context/README.md) and [screening contract](../../docs/features/screening/README.md).
