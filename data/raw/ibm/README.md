# IBM synthetic transaction sources

Expected local input: an IBM transaction CSV such as HI-Small_Trans.csv or HI-Medium_Trans.csv from the publisher-linked distribution. Actual datasets stay local and are not tracked by Git. Optional uploads may include the corresponding publisher accounts CSV and pattern text. Keep variant-specific manifests and audits; see the [HI-Medium workflow](../../README.md#selecting-hi-medium).

The provenance tool requires this exact ordered header, including duplicate Account fields:

```text
Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,Amount Paid,Payment Currency,Payment Format,Is Laundering
```

Run the create and verify commands in [the data workflow](../../README.md). The local output, normally manifest.json, records a relative source path, SHA-256, size, exact header, acquisition/source terms, declared time interpretation and unknown or explicit observation coverage.

A renamed Account.1 header is rejected. The original CSV remains unchanged. UTF-8 with an optional byte-order mark is accepted for the header. Hashes cover original bytes including that mark. Header-only input can be fingerprinted; this does not imply it contains valid transactions.

Optional publisher pattern annotations remain evaluation-only inputs. Do not treat them or Is Laundering values as independent intelligence. The ingest command extracts benchmark labels and normalizes financial records into separate artifact roots. Pattern parsing currently audits block structure; no pattern-driven detector or benchmark matching is implemented.

For a changed file or interpretation, use a new manifest destination instead of replacing an existing manifest. Successful verification checks local consistency, not whether a download is the authoritative publisher version.
