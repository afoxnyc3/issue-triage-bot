# Issue Triage Bot - Demo Summary

## **Use Case**
Auto-triage GitHub issues with AI: classify, prioritize, and route issues in 37 seconds.

**Two deployment options:**
- ⚡ **Haiku** - Fast (37s), cheap, no duplicates
- 🧠 **Sonnet** - Slow (5min), expensive, with memory

---

## **Quick Comparison**

| Feature | haiku-no-memory | main |
|---------|-----------------|------|
| **Model** | Claude Haiku 3.5 | Claude Sonnet 4.5 |
| **Speed** | 37 seconds | 5 minutes |
| **Cost** | ~$0.015/issue | ~$0.15/issue |
| **Memory** | None | PostgreSQL + pgvector |
| **Duplicates** | ❌ | ✅ |
| **Status** | ✅ Stable | ✅ Stable |

> **Note**: Haiku will get memory when [SDK bug #8999](https://github.com/anthropics/claude-code/issues/8999) fixed. See [issue #4](../../issues/4).

---

## **Tech Stack**

### Haiku Branch (Recommended)
- **Agent**: Claude Haiku 3.5
- **MCP**: GitHub only (Docker)
- **Memory**: None
- **Language**: Python 3.13 + uv

### Main Branch
- **Agent**: Claude Sonnet 4.5
- **MCP**: GitHub + PostgreSQL (npx)
- **Memory**: Supabase + pgvector
- **Language**: Python 3.13 + uv

---

## **Workflow**

### Haiku Branch (Fast)
```
Issue Created
    ↓
GitHub Actions Trigger
    ↓
① Fetch Issue (GitHub MCP)
    ↓
② Classify (Bash + AI)
   - Type: bug/feature/docs
   - Priority: P0/P1/P2/P3
    ↓
③ Apply Labels & Comment (GitHub MCP)
```
**Time**: ~37 seconds

### Main Branch (Full-Featured)
```
Issue Created
    ↓
GitHub Actions Trigger
    ↓
① Fetch Issue (GitHub MCP)
    ↓
② Check Memory (PostgreSQL MCP)
   - Search for similar issues
   - Cosine similarity > 85% = duplicate
    ↓
③ Classify (Bash + AI)
   - Type: bug/feature/docs
   - Priority: P0/P1/P2/P3
    ↓
④ Store in Memory (PostgreSQL MCP)
   - INSERT 384-dim embedding
    ↓
⑤ Apply Labels & Comment (GitHub MCP)
```
**Time**: ~5 minutes

---

## **Demo Script**

### Haiku Branch Demo (37 seconds)
1. **Show Code** - `agent.py` lines 69-83 (1 MCP server)
2. **Run Agent** - `uv run python agent.py --issue 1`
3. **Show Speed** - Complete in <40 seconds
4. **GitHub Output** - Labels/comments applied

### Main Branch Demo (5 minutes)
1. **Show Code** - `agent.py` lines 69-92 (2 MCP servers)
2. **Run Agent** - `uv run python agent.py --issue 1`
3. **Show Memory** - Query Supabase for stored embedding
4. **Test Duplicate** - Create similar issue, detect duplicate
5. **GitHub Output** - Labels/comments + duplicate alert

---

## **Key Features**

### Haiku Branch
✅ **Lightning Fast** - 37 seconds per issue
✅ **Ultra Cheap** - ~$0.015 per issue
✅ **Auto-Classification** - AI + keyword matching
✅ **Priority Assessment** - P0-P3 impact analysis

### Main Branch
✅ **Persistent Memory** - PostgreSQL stores all embeddings
✅ **Duplicate Detection** - Semantic similarity via pgvector
✅ **Auto-Classification** - AI + keyword matching
✅ **Priority Assessment** - P0-P3 impact analysis

---

## **Data Schema** (Main Branch Only)

```sql
CREATE TABLE issue_embeddings (
    issue_number INTEGER,
    repo_name TEXT,
    title TEXT,
    body TEXT,
    embedding VECTOR(384),  -- pgvector
    labels JSONB,
    created_at TIMESTAMP
);
```

---

## **Architecture Highlights**

### Haiku Branch
- **Single MCP** - GitHub only (fast startup)
- **No Database** - Stateless operation
- **Event-Driven** - GitHub Actions automation

### Main Branch
- **Multi-MCP** - GitHub + PostgreSQL working together
- **Vector Search** - pgvector for semantic duplicate detection
- **Event-Driven** - GitHub Actions automation
- **Stateful Agent** - Shared persistent memory

---

## **Choose Your Branch**

**Use `haiku-no-memory` if:**
- Speed is priority (8x faster)
- Cost matters (90% cheaper)
- Duplicate detection not critical
- Want simplest setup (no database)

**Use `main` if:**
- Duplicate prevention crucial
- High-quality repo with many issues
- Can afford slower/more expensive
- Need persistent issue history

---

**Repo**: https://github.com/afoxnyc3/issue-triage-bot
**Branches**: `main` (Sonnet+memory) | `haiku-no-memory` (fast)
