# Source of data/bucket_model.json

- Source path: `results/router_dist/bucket_model.json` (repo root)
- Last commit touching the source: `a2fce62af245e2b7e5694ae7e49d4b4a866acbb3`
- Source file identical to that commit (git diff --quiet HEAD): yes
- sha256 of the source: `90066740b062f0fc9566ce3ee98d78fcc2a0cb4cb1b424890f038f5eb9215d38`
- sha256 of this copy:  `90066740b062f0fc9566ce3ee98d78fcc2a0cb4cb1b424890f038f5eb9215d38`
- Copied: 2026-10-15T13:36:08Z with `cp` (byte-for-byte).

Content: the FINAL width-only soft-count Beta model fitted by `router_dist.py` on all 24 tasks after the
cross-validation (see results/router_dist/SPEC.md and report.txt). The headline buckets are under
`bucket_model`; `empty_bucket_cost_fallback_c_bar` is the global cost fallback for widths with no data.
The variants under `variants` are not used by the prototype.
