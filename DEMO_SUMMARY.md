# Issue Triage Bot - Agent Summary

## **Use Case**
Auto-triage GitHub issues with AI: classify, prioritize, detect duplicates using persistent memory.

---

## **Tech Stack**

- **Agent**: Claude Sonnet 4.5 (via Claude Code SDK)
- **Language**: Python 3.13 + uv
- **Memory**: PostgreSQL (Supabase) + pgvector
- **Automation**: GitHub Actions

---

## **MCP Servers (2)**

| Server | Tools | Purpose |
|--------|-------|---------|
| **GitHub MCP** | get_issue, add_labels, add_comment | GitHub API operations |
| **PostgreSQL MCP** | execute_query, list_tables | Database read/write |

---

## **Agent Tools (4)**

1. **mcp__github** - Fetch/update issues
2. **mcp__postgres** - Store/retrieve embeddings
3. **Bash** - Run classification scripts
4. **Read** - Access config files

---

## **Workflow**

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

---

## **Key Features**

✅ **Persistent Memory** - PostgreSQL stores all issue embeddings
✅ **Duplicate Detection** - Semantic similarity via pgvector
✅ **Auto-Classification** - AI + keyword matching
✅ **Priority Assessment** - P0-P3 impact analysis

---

## **Data Schema**

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

## **Demo Script**

1. **Show Code** - `agent.py` lines 69-88 (2 MCP servers)
2. **Run Agent** - `uv run python agent.py --issue 1`
3. **Show Memory** - Query Supabase for stored embedding
4. **Test Duplicate** - Create similar issue, detect duplicate
5. **GitHub Output** - Show labels/comments applied

---

## **Architecture Highlights**

- **Multi-MCP** - 2 different protocols working together
- **Vector Search** - pgvector for semantic analysis
- **Event-Driven** - Automated via GitHub Actions
- **Stateless Agent** - Uses shared persistent memory
