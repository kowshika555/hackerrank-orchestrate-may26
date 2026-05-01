#!/usr/bin/env python3
"""
triage_agent.py — Multi-Domain Support Triage Agent
=====================================================
Processes support tickets from HackerRank, Claude, and Visa using
a retrieval-augmented pipeline grounded strictly on the support corpus.

Usage:
    python triage_agent.py [--input path/to/support_tickets.csv] [--output output.csv]

Author: Triage Agent System
"""

import os
import sys
import json
import random
import argparse
import logging
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

# ── Deterministic seeds ──────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("triage")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = REPO_ROOT / "data"
CORPUS_PATH = DATA_DIR / "corpus.json"

# Candidate input locations (checked in order)
# Covers all common folder layouts including support_tickets/ seen in user screenshots
INPUT_CANDIDATES = [
    # Most common: support_tickets folder at repo root (matches screenshot)
    REPO_ROOT / "support_tickets" / "support_tickets.csv",
    # Alternate folder name
    REPO_ROOT / "support_issues" / "support_tickets.csv",
    # Same folder as the script
    SCRIPT_DIR / "support_tickets.csv",
    # One level up from code/
    REPO_ROOT / "support_tickets.csv",
    # Current working directory variants (handles cd into code/ before running)
    Path.cwd() / "support_tickets.csv",
    Path.cwd() / "support_tickets" / "support_tickets.csv",
    Path.cwd() / "support_issues" / "support_tickets.csv",
    Path.cwd().parent / "support_tickets" / "support_tickets.csv",
    Path.cwd().parent / "support_issues" / "support_tickets.csv",
    Path.cwd().parent / "support_tickets.csv",
    # data/ subfolder variant
    REPO_ROOT / "data" / "support_tickets.csv",
]
SAMPLE_CANDIDATES = [
    REPO_ROOT / "support_tickets" / "sample_support_tickets.csv",
    REPO_ROOT / "support_issues" / "sample_support_tickets.csv",
    SCRIPT_DIR / "sample_support_tickets.csv",
    Path.cwd() / "sample_support_tickets.csv",
    Path.cwd() / "support_tickets" / "sample_support_tickets.csv",
]

# ── Escalation Patterns (rule-based, fast path) ───────────────────────────────
ESCALATION_RULES = [
    (r"\bidentity.{0,20}(stolen|theft|compromise)\b", "fraud/identity theft"),
    (r"\b(fraud|fraudulent).{0,30}(rules|logic|algorithm|internal|detection)\b", "request for internal fraud rules"),
    (r"\binternal.{0,30}(rules|logic|algorithm|policy|fraud)\b", "request for internal rules"),
    # Security vulnerability — must NOT match "HackerRank" or "hackathon"
    (r"\b(security\s+vulnerability|found.{0,20}vulnerability|major\s+security|exploit|zero.?day|cve\b)", "security vulnerability"),
    (r"\b(delete|remove|wipe|destroy).{0,20}(all.{0,10}files|the system|entire\s+database)\b", "malicious/dangerous request"),
    (r"\b(give me|write|provide).{0,30}code.{0,30}(delete|destroy|wipe|rm -rf|format).{0,20}(file|system|disk)\b", "malicious code request"),
    # Score manipulation
    (r"\b(increase|boost|alter|inflate).{0,20}(my\s+)?(score|grade|result)\b", "score manipulation (anti-cheat policy)"),
    (r"\breview.{0,30}(test\s+)?answers.{0,30}(increase|boost|change)\b", "score manipulation (anti-cheat policy)"),
    (r"\burgent.{0,20}cash.{0,30}(no|without|don.t have|dont have).{0,20}(visa|card)\b", "urgent cash without card"),
    (r"\bgive me.{0,30}(internal|confidential|proprietary|all.{0,10}rules)\b", "request for internal/confidential info"),
    (r"afficher.{0,50}règles.{0,30}interne", "request for internal rules (French)"),  # French pattern
    (r"mostrar.{0,50}reglas.{0,30}interna", "request for internal rules (Spanish)"),  # Spanish pattern
]

# ── Company Detection Keywords ────────────────────────────────────────────────
COMPANY_KEYWORDS = {
    "hackerrank": ["hackerrank", "hacker rank", "codechef", "hackerearth", "assessment", "coding test", "screen"],
    "claude": ["claude", "anthropic", "bedrock", "claude.ai", "lti", "conversation", "prompt"],
    "visa": ["visa", "card", "credit card", "debit card", "traveller", "cheque", "cardholder", "merchant", "transaction"],
}

# ── Product Area Mapping ──────────────────────────────────────────────────────
PRODUCT_AREA_MAP = {
    "hackerrank": {
        "test": "assessments", "assessment": "assessments", "candidate": "assessments",
        "score": "assessments", "invite": "assessments", "expir": "assessments",
        "resume": "screen", "profile": "screen", "screen": "screen",
        "subscription": "billing", "billing": "billing", "payment": "billing",
        "api": "api", "integration": "api",
        "team": "general_support", "member": "general_support", "admin": "general_support",
        "cheat": "assessments", "plagiarism": "assessments",
        "community": "community", "contest": "community",
    },
    "claude": {
        "privacy": "privacy", "delete": "privacy", "data": "privacy",
        "export": "conversation_management", "conversation": "conversation_management", "history": "conversation_management",
        "subscription": "subscription", "billing": "subscription", "payment": "subscription",
        "api": "api", "bedrock": "api", "aws": "api",
        "team": "general_support", "invite": "general_support", "member": "general_support",
        "security": "security", "vulnerability": "security",
        "lti": "general_support",
    },
    "visa": {
        "fraud": "fraud", "identity": "security", "stolen": "fraud",
        "travel": "travel_support", "cheque": "travel_support",
        "block": "general_support", "decline": "general_support",
        "dispute": "general_support", "transaction": "general_support",
        "minimum": "general_support", "merchant": "general_support",
        "emergency": "travel_support", "cash": "travel_support",
        "liability": "general_support",
    },
}

# =============================================================================
# RETRIEVAL ENGINE
# =============================================================================

class CorpusRetriever:
    """Loads corpus chunks and retrieves relevant ones using embeddings + BM25-like scoring."""

    def __init__(self, corpus_path: Path):
        log.info("Loading corpus from %s", corpus_path)
        with open(corpus_path) as f:
            self.chunks = json.load(f)
        log.info("Corpus: %d chunks loaded", len(self.chunks))

        # Build embeddings
        self._build_embeddings()

    def _build_embeddings(self):
        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            log.info("Loading sentence-transformers model...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")

            texts = [c["text"] for c in self.chunks]
            log.info("Encoding %d chunks...", len(texts))
            embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)
            embeddings = embeddings.astype("float32")

            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings)
            self.use_embeddings = True
            log.info("FAISS index built (dim=%d)", dim)

        except Exception as e:
            log.warning("Embedding setup failed (%s) — falling back to keyword search", e)
            self.use_embeddings = False

    def retrieve(self, query: str, company: str | None, top_k: int = 3) -> list[dict]:
        """Return top_k chunks most relevant to the query."""
        if self.use_embeddings:
            return self._retrieve_embeddings(query, company, top_k)
        else:
            return self._retrieve_keywords(query, company, top_k)

    def _retrieve_embeddings(self, query: str, company: str | None, top_k: int) -> list[dict]:
        import faiss

        query_vec = self.model.encode([query]).astype("float32")
        faiss.normalize_L2(query_vec)
        scores, indices = self.index.search(query_vec, min(top_k * 3, len(self.chunks)))

        results = []
        seen_topics = set()
        for score, idx in zip(scores[0], indices[0]):
            chunk = self.chunks[idx]
            # Boost score if company matches
            if company and chunk["source"] == company.lower():
                score += 0.15
            # Deduplicate by topic
            topic = chunk.get("topic", "")
            if topic not in seen_topics:
                seen_topics.add(topic)
                results.append((score, chunk))

        results.sort(key=lambda x: -x[0])
        return [c for _, c in results[:top_k]]

    def _retrieve_keywords(self, query: str, company: str | None, top_k: int) -> list[dict]:
        """Simple TF-like keyword scoring fallback."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored = []
        for chunk in self.chunks:
            c_tokens = set(re.findall(r"\w+", chunk["text"].lower()))
            overlap = len(q_tokens & c_tokens)
            bonus = 3 if (company and chunk["source"] == company.lower()) else 0
            scored.append((overlap + bonus, chunk))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:top_k]]


# =============================================================================
# TRIAGE LOGIC
# =============================================================================

def detect_company(issue: str, subject: str, company_raw: str | None) -> str | None:
    """Infer the relevant company from text if not provided."""
    if company_raw and company_raw.strip().lower() not in ("none", "", "nan"):
        c = company_raw.strip().lower()
        if "hackerrank" in c or "hacker" in c:
            return "hackerrank"
        if "claude" in c or "anthropic" in c:
            return "claude"
        if "visa" in c:
            return "visa"
        return c

    text = (issue + " " + (subject or "")).lower()
    scores = {}
    for company, keywords in COMPANY_KEYWORDS.items():
        scores[company] = sum(1 for kw in keywords if kw in text)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def check_escalation(issue: str, subject: str) -> tuple[bool, str]:
    """Check if the ticket must be escalated based on hard rules."""
    combined = (issue + " " + (subject or "")).lower()
    for pattern, reason in ESCALATION_RULES:
        if re.search(pattern, combined, re.IGNORECASE):
            return True, reason
    return False, ""


def infer_product_area(issue: str, company: str | None, retrieved_chunks: list[dict]) -> str:
    """Infer product area from issue keywords and retrieved chunks."""
    text = issue.lower()

    if company and company in PRODUCT_AREA_MAP:
        mapping = PRODUCT_AREA_MAP[company]
        for keyword, area in mapping.items():
            if keyword in text:
                return area

    # Fall back to chunk topic
    if retrieved_chunks:
        chunk = retrieved_chunks[0]
        topic = chunk.get("topic", "").lower()
        source = chunk.get("source", "")
        if source in PRODUCT_AREA_MAP:
            mapping = PRODUCT_AREA_MAP[source]
            for keyword, area in mapping.items():
                if keyword in topic:
                    return area

    return "general_support"


def infer_request_type(issue: str, escalated: bool, escalation_reason: str) -> str:
    """Classify the request type."""
    text = issue.lower()

    if escalated:
        dangerous_patterns = [r"delete.*files", r"malicious", r"exploit", r"hack\b", r"give me.*code"]
        score_patterns = [r"increase.*score", r"boost.*score", r"modify.*answer", r"review.*answers.*increase"]
        internal_patterns = [r"internal.*rules", r"règles.*interne", r"fraud.*rules"]
        for p in dangerous_patterns:
            if re.search(p, text, re.IGNORECASE):
                return "invalid"
        for p in score_patterns:
            if re.search(p, text, re.IGNORECASE):
                return "invalid"
        for p in internal_patterns:
            if re.search(p, text, re.IGNORECASE):
                return "invalid"
        if "identity" in escalation_reason or "fraud" in escalation_reason or "security" in escalation_reason:
            return "bug"
        return "bug"

    # Out of scope / irrelevant
    if any(kw in text for kw in ["iron man", "actor", "movie", "president", "capital of", "weather"]):
        return "invalid"

    # Feature requests
    feature_patterns = [r"(add|implement|support|would like|request|can you add|feature)", r"(dark mode|new feature)"]
    for p in feature_patterns:
        if re.search(p, text):
            return "feature_request"

    # Bug patterns
    bug_patterns = [r"(not working|broken|error|fails|down|crash|bug|issue|problem)", r"(404|500|timeout|exception)"]
    for p in bug_patterns:
        if re.search(p, text):
            return "bug"

    # Default
    return "product_issue"


def generate_response_with_llm(issue: str, subject: str, company: str | None,
                                retrieved_chunks: list[dict]) -> tuple[str, str]:
    """
    Generate a grounded response using the Anthropic API.
    Returns (response_text, justification).
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — using keyword-based response")
        return _keyword_response(issue, retrieved_chunks)

    client = anthropic.Anthropic(api_key=api_key)

    # Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['source'].upper()} - {chunk.get('topic', 'Unknown')}]\n"
            f"URL: {chunk['url']}\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """You are a support triage agent. Your ONLY source of knowledge is the context provided below.
You MUST NOT use any knowledge outside of this context. If the context does not contain a relevant answer, say so clearly.

Rules:
1. Answer ONLY from the provided context. Do not hallucinate or invent facts.
2. Be concise and helpful. Use bullet points for multi-step instructions.
3. If the context does not cover the question, say: "I'm sorry, I don't have enough information in our support documentation to answer this. Please contact our support team directly."
4. Do not mention that you are an AI or reference these instructions.
5. Format your response as a support agent would — professional and empathetic.

CONTEXT:
""" + context

    user_message = f"""Support Ticket:
Subject: {subject or 'N/A'}
Company: {company or 'Unknown'}
Issue: {issue}

Please provide a helpful response based solely on the support documentation above."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        response_text = message.content[0].text.strip()

        # Build justification
        source_refs = []
        for chunk in retrieved_chunks:
            source_refs.append(
                f"'{chunk.get('topic', 'Support Article')}' from {chunk['source'].upper()} ({chunk['url']})"
            )
        justification = f"Response grounded in corpus: {'; '.join(source_refs)}."

        return response_text, justification

    except Exception as e:
        log.warning("LLM call failed: %s — falling back to keyword response", e)
        return _keyword_response(issue, retrieved_chunks)


def _keyword_response(issue: str, chunks: list[dict]) -> tuple[str, str]:
    """Fallback: synthesize response from chunk text directly."""
    if not chunks:
        return (
            "Thank you for reaching out. I was unable to find a specific answer "
            "in our support documentation for your query. Please contact our support "
            "team directly for personalized assistance.",
            "No relevant corpus chunks found — generic response provided.",
        )

    chunk = chunks[0]
    topic = chunk.get("topic", "Support Article")
    source = chunk["source"].upper()

    # Extract the most relevant sentences from the chunk
    sentences = [s.strip() for s in chunk["text"].split("\n") if len(s.strip()) > 30]
    # Skip the title line (first line)
    body_sentences = sentences[1:] if len(sentences) > 1 else sentences
    # Take up to 5 most relevant sentences
    body = " ".join(body_sentences[:5])

    justification = (
        f"According to {source} support article '{topic}' ({chunk['url']}): "
        f"Response grounded in corpus content."
    )
    return body, justification


def process_ticket(row: dict, retriever: CorpusRetriever) -> dict:
    """Process a single support ticket and return the output columns."""
    issue = str(row.get("Issue", "") or "")
    subject = str(row.get("Subject", "") or "")
    company_raw = str(row.get("Company", "") or "")

    log.info("Processing: %s | %s", subject[:60], company_raw)

    # 1. Detect company
    company = detect_company(issue, subject, company_raw)
    log.debug("  → Company: %s", company)

    # 2. Check escalation rules
    must_escalate, escalation_reason = check_escalation(issue, subject)

    # 3. Check for out-of-scope/invalid requests
    combined_lower = (issue + " " + subject).lower()
    is_out_of_scope = _is_out_of_scope(combined_lower, company)

    # 4. Retrieve relevant chunks
    query = f"{subject} {issue}"
    retrieved = retriever.retrieve(query, company, top_k=3)

    # 5. Check if corpus covers the question
    has_coverage = bool(retrieved) and _has_good_coverage(retrieved, query)

    # 6. Determine status and response
    if must_escalate:
        status = "Escalated"
        response = (
            f"This issue requires immediate attention from our specialized team. "
            f"Please be assured your request is being escalated to a human agent "
            f"who can assist you with {escalation_reason}."
        )
        justification = (
            f"Hard escalation rule triggered: {escalation_reason}. "
            f"This request cannot be handled by automated support."
        )
        request_type = infer_request_type(issue, True, escalation_reason)
        product_area = _escalation_product_area(escalation_reason, company)

    elif is_out_of_scope:
        status = "Replied"
        response = "I am sorry, this is out of scope from my capabilities. I can only assist with support issues related to HackerRank, Claude, or Visa."
        justification = "Issue is not related to any supported product/domain. Classified as out-of-scope."
        request_type = "invalid"
        product_area = "conversation_management"

    elif not has_coverage:
        # Check if it's a dangerous/malicious request
        if _is_malicious(combined_lower):
            status = "Escalated"
            response = "This request cannot be processed. It has been flagged and escalated to our trust and safety team."
            justification = "Request appears malicious or violates terms of service."
            request_type = "invalid"
            product_area = "security"
        else:
            # Not covered and not dangerous — escalate
            status = "Escalated"
            response = (
                "Thank you for reaching out. Your request requires assistance from our specialized support team. "
                "An agent will review your case and respond shortly."
            )
            justification = (
                "No relevant information found in the support corpus to answer this query. "
                "Escalating to human agent per policy."
            )
            request_type = infer_request_type(issue, True, "")
            product_area = infer_product_area(issue, company, retrieved)

    else:
        # Generate grounded response
        status = "Replied"
        response, justification = generate_response_with_llm(issue, subject, company, retrieved)
        request_type = infer_request_type(issue, False, "")
        product_area = infer_product_area(issue, company, retrieved)

    return {
        "status": status,
        "product_area": product_area,
        "response": response,
        "justification": justification,
        "request_type": request_type,
    }


def _is_out_of_scope(text: str, company: str | None) -> bool:
    """Check if this is clearly out of scope."""
    # Known out-of-scope patterns
    oos_patterns = [
        r"\b(actor|actress|movie|film|celebrity)\b",
        r"\bpresident\b.{0,40}(which|who|name|of the|states)",
        r"\bwho is the.{0,20}president\b",
        r"\bcapital.{0,20}(of|city)\b",
        r"\bweather\b",
        r"\brecipe\b",
        r"\bsport(s)?\b.{0,20}(score|result|match)",
        r"who.{0,20}(won|win).{0,20}(game|match|championship)",
        r"\bname of the (actor|singer|player|president)\b",
    ]
    for p in oos_patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _is_malicious(text: str) -> bool:
    """Check for malicious/dangerous requests."""
    patterns = [
        r"(rm -rf|del /f|format c:)",
        r"(malware|ransomware|virus|trojan|keylogger)",
        r"(sql injection|xss|cross.site|injection attack)",
        r"give me.{0,20}(password|credential|access token)",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _has_good_coverage(chunks: list[dict], query: str) -> bool:
    """Check if retrieved chunks have meaningful relevance to query."""
    if not chunks:
        return False
    q_tokens = set(re.findall(r"\w{4,}", query.lower()))
    best_overlap = 0
    for chunk in chunks:
        c_tokens = set(re.findall(r"\w{4,}", chunk["text"].lower()))
        overlap = len(q_tokens & c_tokens) / (len(q_tokens) + 1)
        best_overlap = max(best_overlap, overlap)
    return best_overlap > 0.03  # At least 3% token overlap


def _escalation_product_area(reason: str, company: str | None) -> str:
    """Map escalation reason to product area."""
    reason_lower = reason.lower()
    if "fraud" in reason_lower or "identity" in reason_lower:
        return "fraud" if company == "visa" else "security"
    if "security" in reason_lower or "vulnerability" in reason_lower:
        return "security"
    if "score" in reason_lower or "cheat" in reason_lower:
        return "assessments"
    if "cash" in reason_lower:
        return "travel_support"
    if "internal" in reason_lower or "rule" in reason_lower:
        return "general_support"
    return "general_support"


# =============================================================================
# MAIN
# =============================================================================

def find_file(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def main():
    parser = argparse.ArgumentParser(description="Support Triage Agent")
    parser.add_argument("--input", help="Path to support_tickets.csv")
    parser.add_argument("--output", default="support_tickets_output.csv", help="Output CSV path")
    parser.add_argument("--rebuild-corpus", action="store_true", help="Rebuild corpus from web")
    args = parser.parse_args()

    # ── Ensure corpus exists ──────────────────────────────────────────────────
    if args.rebuild_corpus or not CORPUS_PATH.exists():
        log.info("Building corpus...")
        build_script = SCRIPT_DIR / "build_corpus.py"
        if build_script.exists():
            subprocess.run([sys.executable, str(build_script)], check=True)
        else:
            log.error("build_corpus.py not found at %s", build_script)
            sys.exit(1)

    if not CORPUS_PATH.exists():
        log.error("Corpus not found at %s — run build_corpus.py first", CORPUS_PATH)
        sys.exit(1)

    # ── Find input CSV ────────────────────────────────────────────────────────
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = find_file(INPUT_CANDIDATES)

    if not input_path or not input_path.exists():
        log.error("support_tickets.csv not found!")
        log.error("Checked these locations:")
        for p in INPUT_CANDIDATES:
            log.error("  %s", p)
        log.error("")
        log.error("FIX: Run with --input flag pointing to your file, e.g.:")
        log.error("  python triage_agent.py --input ../support_tickets/support_tickets.csv")
        sys.exit(1)

    log.info("Input: %s", input_path)

    # ── Load tickets ──────────────────────────────────────────────────────────
    df = pd.read_csv(input_path)

    # Normalize column names: strip whitespace, fix case variations
    df.columns = [c.strip() for c in df.columns]

    # Ensure required columns exist with flexible name matching
    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl == "issue":
            col_map["Issue"] = col
        elif cl == "subject":
            col_map["Subject"] = col
        elif cl == "company":
            col_map["Company"] = col

    df = df.rename(columns={v: k for k, v in col_map.items()})

    # Add missing columns with defaults
    if "Issue" not in df.columns:
        log.error("CSV must have an Issue column. Found columns: %s", list(df.columns))
        sys.exit(1)
    if "Subject" not in df.columns:
        df["Subject"] = ""
    if "Company" not in df.columns:
        df["Company"] = "None"

    log.info("Loaded %d tickets | Columns: %s", len(df), list(df.columns))

    # ── Init retriever ────────────────────────────────────────────────────────
    retriever = CorpusRetriever(CORPUS_PATH)

    # ── Process each ticket ───────────────────────────────────────────────────
    results = []
    for _, row in df.iterrows():
        result = process_ticket(row.to_dict(), retriever)
        results.append(result)

    # ── Merge and save ────────────────────────────────────────────────────────
    out_df = df.copy()
    for col in ["status", "product_area", "response", "justification", "request_type"]:
        out_df[col] = [r[col] for r in results]

    # Always write to output.csv in the same folder as the input CSV
    # e.g. support_tickets/output.csv  (overwriting the existing placeholder)
    if args.output == "support_tickets_output.csv":
        out_path = input_path.parent / "output.csv"
    else:
        out_path = Path(args.output)

    # Create parent directories if they somehow don't exist
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_df.to_csv(out_path, index=False)
    log.info("✅ Output written to %s (%d rows)", out_path.resolve(), len(out_df))

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TRIAGE SUMMARY")
    print("=" * 60)
    status_counts = out_df["status"].value_counts()
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    print(f"\n  Total tickets processed: {len(out_df)}")
    print(f"  Output file: {out_path.resolve()}")
    print("=" * 60 + "\n")

    # Print per-ticket summary
    print(f"{'#':<4} {'Status':<12} {'Area':<22} {'Type':<16} Subject")
    print("-" * 80)
    for i, (_, row) in enumerate(out_df.iterrows(), 1):
        subj = str(row.get("Subject", ""))[:35]
        print(
            f"{i:<4} {row['status']:<12} {row['product_area']:<22} "
            f"{row['request_type']:<16} {subj}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
