# Issue Triage Bot

**Automatically categorize, label, and route GitHub issues to reduce manual triage time by 80%**

## 🎯 Business Value

- **Time Savings**: Reduces manual triage from 30+ minutes/day to near-zero
- **Faster Response**: Issues get categorized and routed within minutes of creation
- **Better Organization**: Consistent labeling improves searchability and prioritization
- **Duplicate Detection**: Prevents redundant work by identifying similar issues
- **ROI**: Very High - immediate value with minimal complexity

## 📋 What This Agent Does

The Issue Triage Bot monitors GitHub issues and automatically:

1. **Auto-labels** issues based on content analysis (bug, feature, docs, question, etc.)
2. **Detects duplicates** using semantic similarity (AI embeddings)
3. **Assesses priority** (P0-critical, P1-high, P2-medium, P3-low)
4. **Estimates complexity** (simple, medium, complex)
5. **Suggests assignees** based on CODEOWNERS and component ownership
6. **Requests missing information** via comment templates

## 🏗️ Tech Stack

### **Required:**
- **Python 3.11+**
- **uv** (package manager) - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Claude API Key** - Get from [console.anthropic.com](https://console.anthropic.com)
- **GitHub Personal Access Token** - For GitHub MCP server

### **Dependencies:**
```toml
claude-code-sdk = ">=0.0.20"
python-dotenv = ">=1.1.1"
scikit-learn = ">=1.3.0"           # For TF-IDF classification
sentence-transformers = ">=2.2.0"  # For semantic similarity
numpy = ">=1.24.0"
```

### **MCP Servers:**
- **GitHub MCP** (Docker): `ghcr.io/github/github-mcp-server`

### **Optional Enhancements:**
- **SQLite/PostgreSQL**: Store issue embeddings for faster duplicate detection
- **Slack Integration**: Post notifications to team channels

## 📦 Installation

### 1. Clone/Copy This Project

```bash
cd ~/backlog/devops/01-issue-triage-bot
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
GITHUB_TOKEN=github_pat_your-token-here
```

### 4. Configure the Agent

Edit `config.yaml` to customize:
- Classification keywords
- Priority thresholds
- Duplicate detection sensitivity
- Auto-response templates

### 5. Test Locally

```bash
# Run a test classification
uv run python agent.py
```

## 🚀 Deployment Options

### Option 1: GitHub Actions (Recommended)

The included workflow `.github/workflows/triage.yml` runs automatically on every new issue.

**Setup:**
1. Copy `.github/` folder to your repository
2. Add secrets in GitHub Settings → Secrets:
   - `ANTHROPIC_API_KEY`
   - `GITHUB_TOKEN` (usually auto-provided)
3. Push to your repository

The bot will now run on every issue creation!

### Option 2: Self-Hosted Server

Run continuously as a service:

```bash
# Using systemd on Linux
sudo cp triage-bot.service /etc/systemd/system/
sudo systemctl enable triage-bot
sudo systemctl start triage-bot
```

### Option 3: Docker

```bash
docker build -t issue-triage-bot .
docker run -d --env-file .env issue-triage-bot
```

## 📖 Usage

### Automatic Mode

Once deployed via GitHub Actions, the bot runs automatically on:
- New issue creation
- Issue edited/updated

### Manual Trigger

Trigger triage for existing issues:

```bash
# Triage a specific issue
uv run python agent.py --issue 123

# Re-triage all open issues
uv run python agent.py --retriage-all
```

### Via API

```python
from agent import triage_issue

result = await triage_issue(
    issue_number=123,
    owner="your-org",
    repo="your-repo"
)

print(f"Labels: {result['labels']}")
print(f"Priority: {result['priority']}")
print(f"Duplicates: {result['duplicates']}")
```

## 🔧 Configuration

### `config.yaml` Structure

```yaml
classification:
  auto_label: true
  min_confidence: 0.6  # Only label if >60% confident

  labels:
    bug: ["error", "crash", "broken", "fail", "exception"]
    feature: ["feature", "enhancement", "add"]
    docs: ["documentation", "docs", "readme"]

duplicate_detection:
  enabled: true
  similarity_threshold: 0.85  # 85% similar = duplicate
  check_closed_issues: true
  max_age_days: 180  # Only check last 6 months

priority:
  auto_assign: true
  P0_keywords: ["production down", "critical", "security", "data loss"]
  P1_keywords: ["regression", "blocker", "urgent"]

routing:
  use_codeowners: true
  codeowners_file: "CODEOWNERS"
```

### Classification Keywords

Add your own keywords in `config.yaml`:

```yaml
labels:
  performance: ["slow", "lag", "performance", "optimize"]
  security: ["security", "vulnerability", "CVE", "exploit"]
  mobile: ["ios", "android", "mobile", "app"]
```

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/ -v
```

### Test Classification

```bash
# Test on sample issue
uv run python scripts/issue_classifier.py "App crashes when clicking submit button"
# Output: ['bug']
```

### Test Duplicate Detection

```bash
# Find duplicates for issue #123
uv run python scripts/duplicate_detector.py 123
```

## 📊 Monitoring & Metrics

Track bot performance:

```bash
# View triage statistics
python scripts/analytics.py

# Output:
# Total issues triaged: 347
# Auto-labeled: 312 (90%)
# Duplicates found: 23
# Avg response time: 1.2 minutes
```

## 🔍 How It Works

### Architecture

```
GitHub Issue Created
       ↓
GitHub Webhook/Actions Trigger
       ↓
Issue Triage Bot Agent
       ├→ Fetch issue content (GitHub MCP)
       ├→ Classify content (scripts/issue_classifier.py)
       ├→ Check for duplicates (scripts/duplicate_detector.py)
       ├→ Assess priority (scripts/priority_assessor.py)
       ├→ Suggest assignee (scripts/assignee_router.py)
       ↓
Apply Labels & Comment (GitHub MCP)
```

### Classification Algorithm

1. **TF-IDF Vectorization**: Convert issue text to numerical features
2. **Keyword Matching**: Score against category keywords
3. **Confidence Thresholding**: Only label if confidence > threshold
4. **Multi-label Support**: Issues can have multiple labels

### Duplicate Detection

1. **Semantic Embeddings**: Generate vector representations using `sentence-transformers`
2. **Cosine Similarity**: Compare new issue against historical embeddings
3. **Threshold Filtering**: Flag duplicates above similarity threshold (default 85%)
4. **Caching**: Store embeddings in SQLite for fast lookups

## 🛠️ Customization

### Add New Classification Categories

1. Edit `config.yaml`:
```yaml
labels:
  infrastructure: ["docker", "k8s", "deployment", "cicd"]
```

2. The bot will automatically use the new category

### Custom Duplicate Detection Logic

Edit `scripts/duplicate_detector.py`:

```python
def detect_duplicates(new_issue, existing_issues, threshold=0.85):
    # Your custom logic here
    # E.g., weight title similarity higher than body
    pass
```

### Integrate with Slack

Add to `config.yaml`:

```yaml
notifications:
  slack:
    enabled: true
    webhook_url_env: "SLACK_WEBHOOK"
    notify_on:
      - P0_issues
      - duplicates_found
```

## 🐛 Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"
**Solution**: Ensure `.env` file exists and contains valid API key

### Issue: "GitHub token permission denied"
**Solution**: GitHub token needs `repo` and `issues:write` permissions

### Issue: "Duplicate detection very slow"
**Solution**:
- Reduce `max_age_days` in config (check fewer issues)
- Enable embedding cache (SQLite database)
- Limit to open issues only

### Issue: "Classification accuracy poor"
**Solution**:
- Add more keywords to `config.yaml`
- Lower `min_confidence` threshold
- Check if issues need more specific labels

## 📈 Success Metrics

Track these KPIs to measure bot effectiveness:

- **% Auto-labeled**: Target 80%+
- **Duplicate Detection Rate**: Find 90%+ of actual duplicates
- **False Positive Rate**: Keep under 5%
- **Average Triage Time**: Should be under 2 minutes
- **Manual Override Rate**: If high, adjust configuration

## 🔗 Related Resources

- [Claude Code SDK Documentation](https://docs.claude.com/en/docs/claude-code/sdk)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)

## 📄 License

MIT License - See LICENSE file

## 🆘 Support

**Issues with the bot?**
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Test classification scripts individually
4. Open an issue in this repository

---

**Next Steps:**
1. ✅ Review and customize `config.yaml`
2. ✅ Set up environment variables
3. ✅ Test locally with `python agent.py`
4. ✅ Deploy via GitHub Actions
5. ✅ Monitor performance and adjust configuration

Built with ❤️ using [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python)
