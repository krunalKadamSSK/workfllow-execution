# ADR-002: Config Table Task (`configTable`)

**Status:** Accepted  
**Date:** 2026-09-08  
**Branch:** `feature/config-table-task`

## Decision

Add base kind **`configTable`** without changing `userInput` or `table` executors.

- Synapse-shaped `FormField` columns (mapped + extra)
- Query inputs drive Config API filters (resolved by frontend in v1)
- Designer flags: `allowEditFetchedRows`, `allowAddRows`, `allowDeleteRows`
- Aggregations + declared `output` reuse table aggregation helpers

See frontend `docs/config-table-task.md` for full JSON contract and phases.
