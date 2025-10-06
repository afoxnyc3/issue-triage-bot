# Issue Triage Bot ⚡

**Fast GitHub issue classification using Claude Haiku 3.5**

Auto-labels, prioritizes, and routes issues in ~37 seconds.

## Why This Version?

**Speed/Cost Optimized** - Memory disabled for performance:
- ✅ **37 seconds** per issue (vs 5 min with memory)
- ✅ **90% cheaper** API costs (~$0.015 vs $0.15 per issue)
- ❌ No duplicate detection (temporary - see [issue #4](../../issues/4))

**Alternative**: Use `main` branch for Sonnet 4.5 + persistent memory (slower, full-featured)

## What It Does

1. **Auto-labels** - bug, feature, docs, question, etc.
2. **Assesses priority** - P0-critical, P1-high, P2-medium, P3-low
3. **Suggests assignees** - Based on CODEOWNERS
4. **Posts summary** - Structured comment on issue

## Setup

### 1. Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies
```bash
uv sync
```

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
GITHUB_TOKEN=github_pat_your-token-here
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo
```

### 4. Test Locally
```bash
uv run python agent.py --issue 1
```

## Deployment

### GitHub Actions (Recommended)

1. Add repository secrets:
   - `ANTHROPIC_API_KEY`
   - `GITHUB_TOKEN` (auto-provided)

2. Copy workflow file:
```bash
mkdir -p .github/workflows
cp workflows/triage.yml .github/workflows/
```

3. Push to GitHub - bot runs on every new issue!

## Usage

**Triage specific issue:**
```bash
uv run python agent.py --issue 123
```

**Retriage all open issues:**
```bash
uv run python agent.py --retriage-all
```

## Tech Stack

- **Model**: Claude Haiku 3.5 (`claude-3-5-haiku-20241022`)
- **MCP**: GitHub (Docker: `ghcr.io/github/github-mcp-server`)
- **Scripts**: `scripts/issue_classifier.py`
- **Framework**: Claude Code SDK

## Architecture

```
Issue Created → GitHub Webhook → Agent
                                   ↓
                          Fetch (GitHub MCP)
                                   ↓
                          Classify (Bash script)
                                   ↓
                          Label & Comment (GitHub MCP)
```

## Customization

Edit `scripts/issue_classifier.py` to add custom labels:
```python
KEYWORDS = {
    "bug": ["error", "crash", "broken"],
    "feature": ["feature", "enhancement"],
    "security": ["security", "CVE", "vulnerability"],
    # Add your own...
}
```

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
→ Check `.env` file exists and contains valid key

**"GitHub token permission denied"**
→ Token needs `repo` and `issues:write` permissions

**Slow classification**
→ This branch is optimized for speed (~37sec). If slower, check MCP server startup

## Restore Memory Feature

When SDK bug ([anthropics/claude-code#8999](https://github.com/anthropics/claude-code/issues/8999)) is fixed:
1. Add PostgreSQL MCP back to `agent.py`
2. Test Haiku + MCP compatibility
3. Merge memory config from `main` branch

See [issue #4](../../issues/4) for details.

## Branches

- **haiku-no-memory** (this branch) - Fast, cheap, no duplicates
- **main** - Sonnet 4.5 + memory - Slow, expensive, full-featured

---

Built with [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python)
