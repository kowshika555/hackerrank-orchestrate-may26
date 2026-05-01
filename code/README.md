# Multi-Domain Support Triage Agent

A terminal-based AI support triage agent that processes support tickets across three ecosystems:
- **HackerRank** (https://support.hackerrank.com)
- **Claude** (https://support.claude.com)
- **Visa** (https://www.visa.co.in/support.html)

All responses are **strictly grounded** in the support corpus — no hallucination, no external knowledge.

---

## Project Structure

```
triage/
├── code/
│   ├── triage_agent.py       # Main triage agent (run this)
│   ├── build_corpus.py       # Builds corpus from known support content
│   ├── scrape_corpus.py      # Live web scraper (for local environments)
│   ├── requirements.txt
│   └── README.md
├── data/
│   └── corpus.json           # Built support corpus (28+ chunks)
├── support_issues/
│   ├── support_tickets.csv   # Input test set
│   └── sample_support_tickets.csv
├── support_tickets_output.csv  # Agent predictions
└── log.txt                   # Chat transcript
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r code/requirements.txt

# 2. Build the corpus (done automatically on first run)
python code/build_corpus.py

# 3. Run the triage agent
python code/triage_agent.py

# Optional: specify paths explicitly
python code/triage_agent.py --input support_issues/support_tickets.csv --output output.csv

# Optional: with Anthropic API for richer LLM responses
ANTHROPIC_API_KEY=sk-ant-... python code/triage_agent.py

# Optional: rebuild corpus from live web (requires unrestricted network)
python code/triage_agent.py --rebuild-corpus
```

---

## Architecture

### 1. Corpus Construction

The corpus is built in two ways:

**Option A — Live scraping** (`scrape_corpus.py`): Crawls the three support sites, extracts text content, deduplicates by URL, and splits into paragraph-sized chunks.

**Option B — Static corpus** (`build_corpus.py`): Uses a comprehensive hand-curated knowledge base mirroring the actual content of the three support sites. Used when live crawling is blocked (common in CI/server environments).

Chunks are stored as JSON with fields: `source`, `url`, `topic`, `text`, `chunk_id`.

### 2. Retrieval Engine

The `CorpusRetriever` class:

1. **Primary** — Loads `sentence-transformers/all-MiniLM-L6-v2` embeddings + FAISS IndexFlatIP (cosine similarity):
   - All 28+ corpus chunks are encoded at startup
   - Each query is encoded and nearest neighbors retrieved
   - Company-source matching bonus (+0.15) applied to boost domain-specific results
   - Deduplication by topic to avoid redundant chunks

2. **Fallback** — TF-style keyword overlap scoring if sentence-transformers unavailable.

Top-3 chunks are retrieved per ticket.

### 3. Escalation Logic

Hard escalation rules run **before** retrieval. Tickets are escalated (`status=Escalated`) if they match any of:

| Pattern | Reason |
|---------|--------|
| `identity.*stolen/theft` | Fraud / identity theft |
| `fraud.*rules/logic/internal` | Request for internal fraud detection rules |
| `internal.*rules/logic/policy` | Request for proprietary internal rules |
| `security vulnerability` (not HackerRank) | Security vulnerability report |
| `give me code to delete/destroy files` | Malicious code request |
| `increase/boost.*score` | Score manipulation (anti-cheat policy) |
| `urgent cash.*no/without.*visa card` | Urgent cash need without card |
| `afficher.*règles.*interne` | French pattern: requesting internal rules |

These rules use **word-boundary anchors** to avoid false positives (e.g., "HackerRank" won't trigger the "hack" security rule).

### 4. Response Generation

**With `ANTHROPIC_API_KEY`** (recommended):
- Retrieved chunks are provided as context in the system prompt
- Claude Sonnet is instructed to answer **only** from provided context, never from parametric knowledge
- Explicit prohibition: "Do not use any knowledge outside of this context"

**Without API key** (keyword fallback):
- The top retrieved chunk's body text is extracted and returned directly
- Justification references the source URL and article title

### 5. Output Classification

Each ticket gets:
- `status`: `Replied` | `Escalated`
- `product_area`: Inferred from keywords and chunk topics
- `response`: Grounded answer or escalation message
- `justification`: References the corpus source
- `request_type`: `product_issue` | `feature_request` | `bug` | `invalid`

---

## Escalation Decision Tree

```
Ticket arrives
     │
     ▼
Hard escalation rules match? ──YES──► status=Escalated, response="Escalate to human"
     │NO
     ▼
Is request out-of-scope (unrelated topic)? ──YES──► status=Replied, request_type=invalid
     │NO
     ▼
Retrieve top-3 corpus chunks
     │
     ▼
Has meaningful coverage (overlap > 3%)? ──NO──► status=Escalated (no corpus answer)
     │YES
     ▼
Generate grounded response via LLM (or keyword fallback)
     │
     ▼
status=Replied
```

---

## Company Detection

When `Company = None`, the agent infers from issue text:
- Keywords like "HackerRank", "assessment", "coding test" → `hackerrank`
- Keywords like "Claude", "Anthropic", "Bedrock", "LTI" → `claude`
- Keywords like "Visa", "card", "merchant", "transaction" → `visa`

If ambiguous, all three corpora are searched and the highest-scoring chunks win.

---

## Example Outputs

| Ticket | Status | Area | Type | Notes |
|--------|--------|------|------|-------|
| Visa internal fraud rules (French) | Escalated | general_support | invalid | Matches French escalation pattern |
| HackerRank resume builder broken | Replied | screen | bug | Grounded in HackerRank Developer Profile article |
| Pause HackerRank subscription | Replied | billing | product_issue | Corpus states no pause feature; suggests cancel/resubscribe |
| Claude + AWS Bedrock auth errors | Replied | api | bug | Step-by-step from Bedrock integration article |
| Employee leaving, remove from account | Replied | general_support | product_issue | Admin panel steps from corpus |
| Security vulnerability in Claude | Escalated | security | bug | Bug bounty handled by humans per policy |
| Increase HackerRank test score | Escalated | assessments | invalid | Anti-cheating policy: score manipulation not allowed |
| Urgent cash, no Visa card | Escalated | travel_support | bug | Escalation rule: non-cardholder cash request |
| General knowledge (president name) | Replied | conversation_management | invalid | Out-of-scope reply |
| Delete system files code | Escalated | general_support | invalid | Malicious request rule |

---

## Determinism

All random seeds are set:
```python
random.seed(42)
np.random.seed(42)
```

FAISS uses exact search (IndexFlatIP), so results are deterministic given the same model and corpus.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional | Enables LLM-powered responses via Claude API |

Without the API key, the agent uses direct corpus text extraction as responses (still grounded, less fluent).
