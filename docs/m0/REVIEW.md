# M0 source review — architectural review required

Date: 2026-09-18. No OAuth token was accessed and no inference was run.

## Finding and scope

The first candidate Action revision is
`4036a180cf690f49529f5d8c79c998855287f590` (upstream main at review time).
A credential-free check of its actual argument parser fails to preserve the empty
value in the plan's `--tools "" --disallowedTools "mcp__*" --max-turns 2` configuration.
It emits `extraArgs.tools = null`, not an empty string. The nonempty `Read` control,
MCP deny rule and max-turns value are preserved. The defect is the truthiness check
on `nextArg` at lines 159–181 in the pinned parser.

- [Pinned parser source](https://github.com/anthropics/claude-code-action/blob/4036a180cf690f49529f5d8c79c998855287f590/base-action/src/parse-sdk-options.ts#L159)
- [CLI reference](https://code.claude.com/docs/en/cli-reference): documents an empty
  tools value for removing built-ins; MCP denial is separate.
- [Pinned agent-mode setup](https://github.com/anthropics/claude-code-action/blob/4036a180cf690f49529f5d8c79c998855287f590/src/modes/agent/index.ts): explicit prompt selects
  agent mode; MCP registration depends on requested allowed tools.

This is a **source-level argument-preservation failure**, not evidence of actual
model access to tools, an OAuth incompatibility, credential leakage, or billing
misattribution. A bare flag may have CLI-specific semantics; those semantics have
not been established for the resolved runtime. No live checklist item passes on
this evidence. Do not claim the action is exploitable from this check alone.

The execution prompt says: “If a check fails, do not weaken the control merely to
pass. Record the evidence and stop for architectural review.” Work stops at that
review boundary rather than introducing an unverified secret-bearing workflow.
Credential-free M1 work is permitted by the plan, but the explicit failed-M0 stop
condition takes precedence here.

## Reproduce without credentials

Requires Git, Bun and network access to the public upstream/package registry.
This executes only the reviewed option parser, never Claude, GitHub mutations,
authentication commands or model SDK query code. Do not print its entire return
value: it contains a copy of the process environment. The checker outputs only
static flags and source hashes, and rejects a different source hash before import.

From the repository root:

```sh
probe_dir=$(mktemp -d /tmp/triage-m0-parser.XXXXXX)
git clone --quiet https://github.com/anthropics/claude-code-action.git "$probe_dir/upstream"
git -C "$probe_dir/upstream" checkout --detach 4036a180cf690f49529f5d8c79c998855287f590
cp "$probe_dir/upstream/base-action/src/parse-sdk-options.ts" "$probe_dir/parse-sdk-options.ts"
cat > "$probe_dir/package.json" <<'JSON'
{"private":true,"dependencies":{"shell-quote":"1.8.4"}}
JSON
TMPDIR=/private/tmp BUN_INSTALL_CACHE_DIR="$probe_dir/cache" bun install --ignore-scripts --cwd "$probe_dir"
bun scripts/m0/check-action-parser.ts "$probe_dir/parse-sdk-options.ts"
```

Expected exit code: **1**. `parser-contract-result.json` records the allowlisted
result. Bun used: 1.3.14. `shell-quote` version 1.8.4 matches the upstream lockfile.
A missing argument or a changed parser exits 2. Exit 0 means the contract passes.
The checker intentionally fails for this upstream revision; it is not an application
CI test and must not be silently inverted to authorize inference.

## Review decision needed

Choose a reviewed way to establish an empty effective tool inventory before enabling
OAuth inference. Options to investigate include a corrected upstream parser/revision
or a documented deny-all configuration (`--disallowedTools "*"` is currently documented).
The latter was checked only for parser preservation, not runtime behavior. Do not
replace the empty-inventory acceptance criterion with a list of approved tools or
with model assurances. Any revised configuration must pass the same live checks.
A fork, alternative runtime, broader permissions or billing change is not authorized.

## Live acceptance checklist — all pending

- [ ] An issue opened by a non-collaborator triggers the action.
- [ ] The supplied GITHUB_TOKEN is read-only; no App-token fallback is used.
- [ ] Effective model tool inventory is empty.
- [ ] A deliberately requested disallowed GitHub write is denied.
- [ ] Environment/file canary cannot appear in structured output.
- [ ] Structured output is produced and locally validated.
- [ ] No raw prompts/bodies, OAuth credential or canary leaks in artifacts or unexpected logs.
- [ ] Owner confirms personal Max usage attribution, not Team or API billing.
- [ ] Token issue date and observed rotation/expiry behavior recorded without the value.

Normal output hides tool inventory in the reviewed action; inspect the temporary
execution file locally on the ephemeral runner and emit only validated metadata.
Do not enable full/debug output to obtain the inventory: the parser turns full
output on when ACTIONS_STEP_DEBUG is true, and transcripts can contain issue data.
This inspection strategy is still to be implemented and tested after review.

## Exact owner-operated sequence after review

1. Resolve the tool-isolation review; resume Codex to implement/review the harness.
2. Separately authorize publishing the reviewed harness when ready (no push in this task).
3. Outside Codex, open Claude Code and use `/status` to confirm personal Max identity.
4. Outside Codex, run `claude setup-token` and store the result directly as the GitHub
   repository secret `CLAUDE_CODE_OAUTH_TOKEN`. Never paste it into Codex or a file.
5. Run the approved live harness with a non-collaborator test issue and supply only
   the redacted run/checklist evidence and billing/rotation attestations.

No runnable M0 workflow has been installed. The legacy workflow remains unchanged
locally and remotely; disable/make it manual-only at the first implementation
checkpoint before validating the replacement. Legacy deletion waits for cutover.
