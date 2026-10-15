# IBM benchmark acquisition and limitations

## Source
Use the Kaggle distribution linked by [IBM AML-Data](https://github.com/IBM/AML-Data):
[IBM Transactions for Anti Money Laundering](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml).

The initial variant is HI-Small. Source data stays local and is not included in Git. Download access may require an account or acceptance of source terms; record those conditions. Never embed credentials in scripts or documentation. Implemented audit, manifest, verify, normalization and publisher-account commands are documented in [data/README.md](../data/README.md).

IBM describes the data as fully synthetic and identifies the data license as CDLA-Sharing-1.0, separately from the repository code license. Keep acquisition and redistribution decisions tied to the exact downloaded files.

## Expected raw input
Place the transaction CSV under `data/raw/ibm/`. Preserve the original name and content. Optional publisher pattern files, if acquired, are benchmark evaluation annotations only. A manifest is required before normalization.

Verify this ordered header against the acquired variant:
```text
Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,Amount Paid,Payment Currency,Payment Format,Is Laundering
```
Stop on an incompatible header rather than guessing. A CSV reader may rename duplicate fields; positional verification must happen before relying on renamed columns.

## Supported observations
The transaction export supports transfer endpoints, bank identities, times, amounts, currencies, payment formats and separate laundering labels. A separately supplied accounts CSV contains synthetic entity IDs/names; preserve it separately with source provenance and explicit link diagnostics. Neither file proves real customer identity, intent, verified ownership, account age, source of wealth or balances.

Accounts can be derived from endpoints. Customer records cannot be recovered from account IDs. Currency changes and amount differences do not establish fees or exchange rates.

## Capability gates
- Seven-day historical rules require a complete eligible prior interval. A short source period can make them unavailable.
- Source timestamps with minute precision cannot establish within-minute event order.
- A payment format must not be equated to cash withdrawal or a crypto exchange without a verified mapping.
- Do not infer countries from opaque bank IDs.
- No benchmark ground truth may enter detection-facing files or queries.
- Cross-bank relationships are visible in this synthetic benchmark; a deployment at one bank may have less visibility.

## Provenance workflow
1. Acquire from the publisher-linked distribution.
2. Record variant, source terms, acquisition time and original path.
3. Compute cryptographic file hashes and verify the header.
4. Declare timezone interpretation and known observation intervals.
5. Normalize into separate transaction and benchmark-label artifacts.
6. Persist lineage and quality diagnostics; keep originals immutable.

A small handcrafted example used in future tests must be labelled a test fixture and must never be represented as a slice of the IBM benchmark.
