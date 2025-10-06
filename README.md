# Issue Triage Bot 🤖

**Automatically categorize, prioritize, and route GitHub issues using AI**

## Choose Your Branch

### ⚡ **haiku-no-memory** (Recommended)
- **Speed**: ~37 seconds per issue
- **Cost**: ~$0.015 per issue
- **Trade-off**: No duplicate detection
- **Best for**: Fast triage, cost-conscious projects

### 🧠 **main** (This Branch)
- **Speed**: ~5 minutes per issue
- **Cost**: ~$0.15 per issue
- **Features**: Persistent memory + duplicate detection
- **Best for**: High-quality repos needing duplicate prevention

> **Note**: Haiku branch is faster due to [SDK bug](https://github.com/anthropics/claude-code/issues/8999) - memory will be added to Haiku once resolved. See [issue #4](../../issues/4) for details.

---

## What It Does

1. **Auto-labels** - bug, feature, docs, question, etc.
2. **Detects duplicates** - Using semantic similarity (this branch only)
3. **Assesses priority** - P0-critical, P1-high, P2-medium, P3-low
4. **Suggests assignees** - Based on CODEOWNERS
5. **Posts summary** - Structured comment

## Quick Start

### 1. Install
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 2. Configure
```bash
cp .env.example .env
```

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
GITHUB_TOKEN=github_pat_your-token-here
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo
DATABASE_URL=postgresql://...  # This branch only
```

### 3. Test
```bash
uv run python agent.py --issue 1
```

## Deployment

### GitHub Actions
```bash
mkdir -p .github/workflows
cp workflows/triage.yml .github/workflows/
```

Add secrets to your repo:
- `ANTHROPIC_API_KEY`
- `DATABASE_URL` (this branch only)

Push to GitHub - bot runs on every new issue!

## Tech Stack

**Main Branch**:
- Model: Claude Sonnet 4.5
- MCP: GitHub + PostgreSQL
- Memory: Supabase (pgvector)

**Haiku Branch**:
- Model: Claude Haiku 3.5
- MCP: GitHub only
- Memory: None (temporary)

## Architecture

```
Issue → Webhook → Agent
                    ↓
           Fetch (GitHub MCP)
                    ↓
           Check Memory (PostgreSQL MCP) [main only]
                    ↓
           Classify (Bash script)
                    ↓
           Label & Comment (GitHub MCP)
```

## Usage

**Triage specific issue:**
```bash
uv run python agent.py --issue 123
```

**Retriage all:**
```bash
uv run python agent.py --retriage-all
```

## Customization

Edit `scripts/issue_classifier.py`:
```python
KEYWORDS = {
    "bug": ["error", "crash", "broken"],
    "feature": ["feature", "enhancement"],
    # Add custom labels...
}
```

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
→ Check `.env` exists with valid key

**"GitHub token permission denied"**
→ Token needs `repo` + `issues:write` permissions

**Slow performance**
→ Try `haiku-no-memory` branch for 8x speedup

**PostgreSQL connection fails** (main branch)
→ Check `DATABASE_URL` format and credentials

## Branch Comparison

| Feature | main | haiku-no-memory |
|---------|------|-----------------|
| Speed | 5 min | 37 sec |
| Cost/issue | ~$0.15 | ~$0.015 |
| Duplicate detection | ✅ | ❌ |
| Memory | PostgreSQL | None |
| Model | Sonnet 4.5 | Haiku 3.5 |
| Stability | ✅ | ✅ |

## Files

- `agent.py` - Main agent logic
- `scripts/issue_classifier.py` - Classification keywords
- `scripts/memory_manager.py` - Embedding generation (main only)
- `supabase/migrations/` - Database schema (main only)

---

**Built with** [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python)
