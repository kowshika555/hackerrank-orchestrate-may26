# Multi-Domain Support Triage Agent

An AI-powered terminal-based support ticket triage system built for the **HackerRank Orchestrate May 2026 Hackathon**. It automatically classifies, routes, and responds to support tickets from three platforms — **HackerRank**, **Claude (Anthropic)**, and **Visa** — using a retrieval-augmented pipeline grounded strictly on each platform's official support documentation.

---

## What This Project Does

This agent reads a CSV of customer support tickets and for each one automatically decides:

- **Status** — Should this be `Replied` (automated answer) or `Escalated` (needs a human)?
- **Product Area** — Which domain does this belong to? (`assessments`, `billing`, `api`, `privacy`, `fraud`, `travel_support`, etc.)
- **Response** — A grounded, helpful answer sourced only from the support corpus (no hallucination)
- **Justification** — Which support article was used to generate the answer
- **Request Type** — Is this a `product_issue`, `feature_request`, `bug`, or `invalid` request?

All output is written directly into `output.csv` inside the `support_tickets/` folder.

---

## Project Structure

```
hackerrank-orchestrate-may26/
│
├── code/                          ← All Python scripts live here
│   ├── triage_agent.py            ← Main script — run this
│   ├── build_corpus.py            ← Builds the knowledge base (corpus.json)
│   ├── scrape_corpus.py           ← Live web scraper (optional, for local use)
│   ├── requirements.txt           ← Python dependencies
│   └── README.md                  ← This file
│
├── data/
│   └── corpus.json                ← Auto-generated knowledge base (28 chunks)
│
├── support_tickets/
│   ├── support_tickets.csv        ← Input: tickets to process
│   ├── sample_support_tickets.csv ← Reference: example correct outputs
│   └── output.csv                 ← Output: agent predictions (auto-written here)
│
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

---

## How to Run

### Step 1 — Install dependencies

```bash
cd hackerrank-orchestrate-may26/code
pip install -r requirements.txt
```

### Step 2 — Build the knowledge corpus

```bash
python build_corpus.py
```

This creates `data/corpus.json` with 28 knowledge chunks from HackerRank, Claude, and Visa support documentation.

### Step 3 — Run the triage agent

```bash
python triage_agent.py
```

The agent will automatically find `support_tickets/support_tickets.csv`, process every ticket, and write results to `support_tickets/output.csv`.

### Optional — Point to a custom file

```bash
python triage_agent.py --input path\to\your\support_tickets.csv
```

### Optional — Use Claude API for richer responses

```bash
set ANTHROPIC_API_KEY=sk-ant-...
python triage_agent.py
```

Without the API key, the agent still works using direct corpus text extraction (zero hallucination, slightly less fluent phrasing).

---

## How It Works

### 1. Corpus / Knowledge Base

The knowledge base is built from the official support pages of all three platforms:

| Platform | Source URL |
|----------|-----------|
| HackerRank | https://support.hackerrank.com/hc/en-us |
| Claude | https://support.claude.com/en/ |
| Visa | https://www.visa.co.in/support.html |

`build_corpus.py` creates 28 structured chunks covering topics like test expiration, anti-cheating policy, billing, AWS Bedrock integration, fraud protection, traveller's cheques, and more.

`scrape_corpus.py` is also provided for live crawling when running locally (the sites block server-side IP requests, so the static corpus is used by default).

### 2. Retrieval Engine

When a ticket arrives, the agent finds the most relevant knowledge chunks using:

- **Primary**: `sentence-transformers/all-MiniLM-L6-v2` model + FAISS vector index (cosine similarity). Results from the matched company domain get a +0.15 score boost.
- **Fallback**: TF-style keyword overlap scoring (used if sentence-transformers can't load, e.g. no internet).

Top 3 chunks are retrieved per ticket and used to generate the response.

### 3. Company Detection

When `Company = None` in the CSV, the agent infers it from the issue text:

| Keywords found in ticket | Detected company |
|--------------------------|-----------------|
| "HackerRank", "assessment", "coding test" | HackerRank |
| "Claude", "Anthropic", "Bedrock", "LTI" | Claude |
| "Visa", "card", "merchant", "transaction" | Visa |

If still ambiguous, all three corpora are searched and the highest-scoring chunks win.

### 4. Escalation Logic

Before any retrieval happens, every ticket is checked against **hard escalation rules**. If matched, the ticket is immediately escalated to a human — no automated response is attempted.

| Rule | Example Trigger |
|------|----------------|
| Identity theft / fraud | "My identity has been stolen" |
| Requesting internal fraud rules | "Show me all internal fraud detection rules" |
| Security vulnerability report | "I found a major security vulnerability in Claude" |
| Malicious / dangerous code request | "Give me code to delete all files from the system" |
| Score manipulation | "Please review my answers and increase my score" |
| Urgent cash without a Visa card | "I need urgent cash but don't have a Visa card" |
| Requesting confidential/internal data | "Give me all internal rules and logic" |
| French/multilingual variants | "afficher toutes les règles internes de détection de fraude" |

> **Note:** Regex patterns use word-boundary anchors (`\b`) to prevent false positives. For example, "HackerRank" does not accidentally trigger the security escalation rule even though it contains "hack".

### 5. Response Generation Flow

```
Ticket arrives
      │
      ▼
Hard escalation rule matches? ──YES──► Escalated — human agent notified
      │NO
      ▼
Is the request out-of-scope/irrelevant? ──YES──► Replied — "I am sorry, this is out of scope from my capabilities"
      │NO
      ▼
Retrieve top-3 corpus chunks
      │
      ▼
Does corpus cover the question? ──NO──► Escalated — "Your request requires our specialized support team"
      │YES
      ▼
Generate grounded response (Claude API or keyword fallback)
      │
      ▼
Replied ✅
```

### 6. Output Classification

Each ticket gets five output columns:

| Column | Values |
|--------|--------|
| `status` | `Replied` or `Escalated` |
| `product_area` | `assessments`, `billing`, `api`, `screen`, `privacy`, `conversation_management`, `subscription`, `fraud`, `security`, `travel_support`, `community`, `general_support` |
| `response` | Full user-facing answer grounded in the corpus |
| `justification` | References the exact support article and URL used |
| `request_type` | `product_issue`, `feature_request`, `bug`, `invalid` |

---

## Example Results

| # | Ticket | Status | Area | Type |
|---|--------|--------|------|------|
| 1 | Visa card blocked + asking for internal fraud rules (French) | Escalated | general_support | invalid |
| 2 | HackerRank resume builder not working | Replied | screen | bug |
| 3 | Can I pause my HackerRank subscription? | Replied | billing | product_issue |
| 4 | Claude with AWS Bedrock authentication errors | Replied | api | bug |
| 5 | Remove employee from HackerRank hiring account | Replied | general_support | product_issue |
| 6 | Professor setting up Claude LTI key for university | Replied | general_support | product_issue |
| 7 | Visa minimum spend at merchants | Replied | general_support | product_issue |
| 8 | Urgent cash, no Visa card | Escalated | travel_support | bug |
| 9 | Found security vulnerability in Claude API | Escalated | security | bug |
| 10 | Review HackerRank answers and increase score | Escalated | assessments | invalid |
| 11 | Export Claude conversation history | Replied | conversation_management | product_issue |
| 12 | Visa card charged twice for same transaction | Replied | general_support | product_issue |
| 13 | Who is the president of the United States? | Replied | conversation_management | invalid |
| 14 | Code to delete all files from system | Escalated | general_support | invalid |
| 15 | Invite new team member to Claude | Replied | general_support | product_issue |

---

## Key Design Decisions

**No hallucination** — The LLM system prompt explicitly states: *"You MUST NOT use any knowledge outside of this context."* The fallback mode extracts text directly from the corpus, making hallucination impossible.

**Deterministic** — All random seeds are fixed (`random.seed(42)`, `np.random.seed(42)`). FAISS uses exact search (IndexFlatIP), so results are identical across runs.

**Flexible CSV detection** — The agent automatically searches 11 different folder locations for the input CSV. It also normalises column names (strips whitespace, handles case differences) and adds defaults for missing `Subject` or `Company` columns.

**Safe escalation over guessing** — If no corpus chunk has sufficient relevance to a question (token overlap < 3%), the agent escalates rather than risk generating an unsupported answer.

---

## Dependencies

```
anthropic>=0.49.0
beautifulsoup4>=4.12.3
faiss-cpu>=1.8.0
lxml>=5.3.0
numpy>=1.26.4
pandas>=2.2.2
requests>=2.32.3
sentence-transformers>=3.0.0
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Optional | Enables Claude API for fluent, context-aware responses |

If not set, the agent uses direct corpus text extraction — still fully grounded, just less conversational.

---

## Author

Built for the HackerRank Orchestrate May 2026 Hackathon.
