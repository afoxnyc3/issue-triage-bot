# Deterministic operator commands

Install the locked environment with `uv sync --locked`. Run `uv run --locked triage
--help` for options. Python never invokes Claude. Commands below describe the future
approved runtime; development verification uses mocked GitHub and ephemeral test
keys. No live command has been run as acceptance evidence.

## Apply and inspect

`triage apply --repo OWNER/REPO --issue NUMBER --input decision.json --dry-run`
fetches the live release and full issue, validates the proposal, and prints redacted
JSON with intended outcome, decision hash and planned comment/label operations.
`--audit audit.json` writes that same record. An omitted input represents an inference
failure and follows the bounded human-review/retry policy. Disabled control exits
without loading signing keys. Dry-run and shadow policy never write.

`--write` additionally requires a preflight `--envelope envelope.json` and matching
GitHub workflow context: repository, run ID, attempt and the issues or workflow_dispatch
event file. It does not bypass rollout, content, policy, prompt, generation, signing
or timeline fences. `--force` allows explicit reclassification of unchanged content;
it does not override these controls. Canary type-label writes currently defer because
the durable mutation reservation adapter is not yet wired. This CLI is not a finished
production entry point until M0 and workflow acceptance pass.

`triage check --repo OWNER/REPO` lists missing policy/control/health labels and returns
nonzero when setup is needed. `triage setup-labels --repo OWNER/REPO` previews creation;
explicit `--write` requires an enabled live release and rechecks its entire identity
before each creation. It never edits or deletes existing label definitions.

`triage repair --repo OWNER/REPO --dry-run` inspects up to 50 issues in creation order,
including closed issues, and reports authenticated pending/final or unreadable state.
Use repeated `--issue NUMBER` for selection or `--limit N` (maximum 500). A truncated
report is explicitly marked. Repair is inspection only: it never guesses ownership,
overwrites forged/duplicate comments or silently repairs unknown signing keys.

## Runtime environment

The operator/workflow supplies `GITHUB_TOKEN` with only the permissions needed by the
command. Read commands need repository contents/issues read access; explicit writes
need issues write. Apply and repair also require `TRIAGE_STATE_HMAC_KEY_ID` and
`TRIAGE_STATE_HMAC_KEY` (base64 encoding of at least 32 bytes). During rotation supply
both `TRIAGE_STATE_HMAC_PREVIOUS_KEY_ID` and `TRIAGE_STATE_HMAC_PREVIOUS_KEY`; new states
use the current key. Provision and rotate secrets outside Codex. Never put key values
in arguments, files committed to Git, reports, artifacts or chat.

Apply write context uses `GITHUB_REPOSITORY`, `GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT`,
`GITHUB_EVENT_NAME`, and `GITHUB_EVENT_PATH`. Local dry-run uses synthetic run 1/attempt
1 when IDs are absent. Python neither requires nor reads the Claude OAuth credential.
Errors are intentionally redacted; no traceback locals or raw model/API payloads are
printed. CLI failures before an ApplyRecord exists may emit only a redacted error;
the workflow must supply its own missing-audit failure record in that case.
