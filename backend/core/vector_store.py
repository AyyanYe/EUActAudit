# backend/core/vector_store.py
"""
Lightweight article retrieval for EU AI Act.
Uses TF-IDF + cosine similarity over ~35 structured articles.
No external vector DB needed — runs in-memory with just numpy.
"""

import os
import json
import math
import re
from collections import Counter

# Path to the ingested articles JSON
ARTICLES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "eu_ai_act_articles.json"
)

# In-memory cache
_articles: list[dict] | None = None
_tfidf_matrix: list[dict] | None = None
_idf: dict | None = None


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric, remove stopwords."""
    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "ought",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "and",
        "but",
        "or",
        "if",
        "while",
        "because",
        "until",
        "that",
        "which",
        "who",
        "whom",
        "this",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "him",
        "her",
        "his",
        "what",
        "any",
        "also",
        "about",
        "up",
        "just",
        "whether",
        "upon",
    }
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _build_idf(docs: list[list[str]]) -> dict:
    """Compute inverse document frequency."""
    n = len(docs)
    df = Counter()
    for doc in docs:
        df.update(set(doc))
    return {term: math.log((n + 1) / (count + 1)) + 1 for term, count in df.items()}


def _tfidf_vector(tokens: list[str], idf: dict) -> dict:
    """Compute TF-IDF vector for a token list."""
    tf = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {term: (count / total) * idf.get(term, 1.0) for term, count in tf.items()}


def _cosine_similarity(v1: dict, v2: dict) -> float:
    """Cosine similarity between two sparse vectors (dicts)."""
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    mag1 = math.sqrt(sum(v**2 for v in v1.values()))
    mag2 = math.sqrt(sum(v**2 for v in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _load_articles():
    """Load articles from JSON and build TF-IDF index."""
    global _articles, _tfidf_matrix, _idf

    if _articles is not None:
        return

    if not os.path.exists(ARTICLES_PATH):
        print(
            f"[WARNING] Articles file not found at {ARTICLES_PATH}. Run 'python ingest_eu_ai_act.py' first."
        )
        _articles = []
        _tfidf_matrix = []
        _idf = {}
        return

    with open(ARTICLES_PATH, "r", encoding="utf-8") as f:
        _articles = json.load(f)

    # Build TF-IDF index
    tokenized_docs = []
    for art in _articles:
        # Combine title + text for richer matching
        combined = (
            f"{art.get('article', '')} {art.get('title', '')} {art.get('text', '')}"
        )
        tokenized_docs.append(_tokenize(combined))

    _idf = _build_idf(tokenized_docs)
    _tfidf_matrix = [_tfidf_vector(doc, _idf) for doc in tokenized_docs]

    print(f"[RAG] Loaded {len(_articles)} EU AI Act articles into memory.")


def query_articles(query_text: str, n_results: int = 5) -> list[dict]:
    """
    Semantic search over EU AI Act articles using TF-IDF + cosine similarity.
    Returns a list of dicts: [{"article": ..., "title": ..., "text": ..., "score": ...}, ...]
    """
    _load_articles()

    if not _articles or not _tfidf_matrix:
        return []

    query_tokens = _tokenize(query_text)
    query_vec = _tfidf_vector(query_tokens, _idf)

    scored = []
    for i, doc_vec in enumerate(_tfidf_matrix):
        score = _cosine_similarity(query_vec, doc_vec)
        if score > 0:
            scored.append((score, i))

    scored.sort(reverse=True)
    results = []
    for score, idx in scored[:n_results]:
        art = _articles[idx]
        results.append(
            {
                "article": art.get("article", "Unknown"),
                "title": art.get("title", ""),
                "text": art.get("text", ""),
                "score": round(score, 4),
            }
        )
    return results


# Topic-to-query mapping for known compliance topics
_TOPIC_QUERIES = {
    "human_oversight": "human oversight high-risk AI systems intervene override stop button Article 14",
    "data_governance": "data governance training data quality bias mitigation representative datasets Article 10",
    "accuracy_robustness": "accuracy robustness cybersecurity error rates resilience adversarial attacks Article 15",
    "record_keeping": "record keeping logging traceability automatic recording events logs Article 12",
    "transparency": "transparency obligations disclosure AI interaction users informed Article 50",
    "risk_classification": "classification high-risk AI systems Annex III categories Article 6",
    "prohibited_practices": "prohibited AI practices social scoring emotion recognition biometric ban Article 5",
    "conformity_assessment": "conformity assessment procedures notified body CE marking Article 43",
    "post_market_monitoring": "post-market monitoring surveillance performance data collection Article 72",
    "fundamental_rights": "fundamental rights impact assessment high-risk deployers Article 27",
    "quality_management": "quality management system provider compliance procedures Article 17",
    "technical_documentation": "technical documentation system description development process Article 11",
    "risk_management": "risk management system lifecycle iterative risk identification mitigation Article 9",
    "penalties": "penalties fines infringements administrative sanctions Article 99",
    "provider_obligations": "obligations providers high-risk AI systems compliance Article 16",
    "deployer_obligations": "obligations deployers high-risk AI systems monitoring input data Article 26",
    "general_purpose_ai": "general-purpose AI models systemic risk obligations providers Article 53",
    "registration": "registration EU database high-risk AI systems placing on market Article 49",
    "timeline": "entry into force application timeline dates prohibited practices high-risk Article 113",
}


def query_by_topic(topic_key: str, n_results: int = 3) -> str:
    """
    Given a compliance topic key (e.g. 'human_oversight', 'data_governance'),
    return concatenated relevant article text for LLM context injection.
    """
    query = _TOPIC_QUERIES.get(topic_key, topic_key.replace("_", " "))
    results = query_articles(query, n_results=n_results)

    if not results:
        return ""

    chunks = []
    for r in results:
        header = f"[{r['article']}] {r['title']}" if r["title"] else r["article"]
        chunks.append(f"{header}\n{r['text']}")

    return "\n\n---\n\n".join(chunks)


def identify_relevant_articles(
    domain: str, purpose: str, workflow_steps: list, n_results: int = 8
) -> list[dict]:
    """
    Given a business description and workflow, identify which EU AI Act articles are most relevant.
    Returns a list of dicts: [{"article": ..., "title": ..., "text": ..., "score": ...}, ...]

    This is used at CHECKPOINT to dynamically determine which articles to evaluate,
    rather than always checking the same 4 hardcoded articles.
    """
    workflow_str = " -> ".join(workflow_steps) if workflow_steps else ""
    query = f"{domain} {purpose} AI system"
    if workflow_str:
        query += f" workflow: {workflow_str}"
    results = query_articles(query, n_results=n_results)
    return results


def is_populated() -> bool:
    """Check if the articles JSON exists and has content."""
    _load_articles()
    return bool(_articles)
