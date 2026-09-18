/** Credential-free M0 contract check. Never invoke Claude or print the SDK environment. */
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const parserPath = resolve(process.argv[2] ?? '');
if (!process.argv[2]) {
  console.error('Usage: bun check-action-parser.ts /isolated/path/parse-sdk-options.ts');
  process.exit(2);
}
const source = await readFile(parserPath);
const parserHash = createHash('sha256').update(source).digest('hex');
const reviewedHash = 'b42cc8daa1d15fb00321784cec375b1c855bb2e41bf03b37dfd462385f9e5548';
if (parserHash !== reviewedHash) {
  console.error('Parser does not match reviewed source; review the new revision first.');
  process.exit(2);
}
const { parseSdkOptions } = await import(pathToFileURL(parserPath).href);
const empty = parseSdkOptions({
  claudeArgs: '--tools "" --disallowedTools "mcp__*" --max-turns 2',
});
const nonempty = parseSdkOptions({
  claudeArgs: '--tools "Read" --disallowedTools "mcp__*" --max-turns 2',
});
const checks = {
  empty_tools_preserved: empty.sdkOptions.extraArgs?.tools === '',
  nonempty_tools_preserved: nonempty.sdkOptions.extraArgs?.tools === 'Read',
  mcp_denial_preserved: JSON.stringify(empty.sdkOptions.disallowedTools) === '["mcp__*"]',
  max_turns_preserved: empty.sdkOptions.maxTurns === 2,
};
// Allowlisted static metadata only. sdkOptions.env contains the host environment:
// serializing the full result would violate the credential-handling requirement.
console.log(JSON.stringify({
  action_sha: '4036a180cf690f49529f5d8c79c998855287f590',
  parser_sha256: parserHash,
  checks,
  observed_empty_tools_value: empty.sdkOptions.extraArgs?.tools ?? null,
  passed: Object.values(checks).every(Boolean),
}, null, 2));
process.exitCode = Object.values(checks).every(Boolean) ? 0 : 1;
