"""Query intent extraction module.

Derives a structured representation of user query intent prior to retrieval.
Supports arbitrary legal/business queries without hardcoding specific topics.
"""

from __future__ import annotations

import re

from backend.models.schemas import QueryIntent
from backend.parsing.metadata import extract_entities, extract_topics


def extract_query_intent(query: str) -> QueryIntent:
    """Extract a structured query intent from a user query string.

    Identifies primary topic, subtopics, relationship intent (conflict,
    override, consistent), requested attributes, and expected answer type.

    Args:
        query: User's question or prompt string.

    Returns:
        Structured QueryIntent model.
    """
    query_lower = query.lower()

    # 1. Topic extraction via open taxonomy
    topics = extract_topics(query)
    primary_topic = topics[0] if topics else None

    # Topic fallback heuristics for specific business terms
    if not primary_topic:
        if any(w in query_lower for w in ["retention", "renewal", "duration", "period"]):
            primary_topic = "term_duration"
        elif any(w in query_lower for w in ["ip", "patent", "copyright", "ownership"]):
            primary_topic = "intellectual_property"
        elif any(w in query_lower for w in ["cap", "limit", "liability"]):
            primary_topic = "liability"
        elif any(w in query_lower for w in ["deadline", "payment", "invoice", "fee"]):
            primary_topic = "payment"

    # 2. Subtopics
    subtopics: list[str] = []
    if any(w in query_lower for w in ["notice", "notice period", "notice_period"]):
        subtopics.append("notice_period")
    if any(w in query_lower for w in ["renewal", "extension"]):
        subtopics.append("renewal")
    if any(w in query_lower for w in ["retention", "storage"]):
        subtopics.append("retention")
    if any(w in query_lower for w in ["deadline", "due date", "due"]):
        subtopics.append("deadline")

    # 3. Relationship & comparison intent detection
    has_comparison = False
    relationship_intent: str | None = None

    conflict_keywords = [
        "conflict",
        "conflicting",
        "contradict",
        "contradictory",
        "inconsistent",
        "different",
        "mismatch",
        "discrepancy",
        "differ",
        "vary",
        "clash",
    ]
    override_keywords = ["override", "supersede", "amend", "amendment", "prevail"]
    consistent_keywords = ["consistent", "compatible", "match", "agree", "harmonious"]

    if any(k in query_lower for k in conflict_keywords):
        has_comparison = True
        relationship_intent = "conflict"
    elif any(k in query_lower for k in override_keywords):
        has_comparison = True
        relationship_intent = "override"
    elif any(k in query_lower for k in consistent_keywords):
        has_comparison = True
        relationship_intent = "consistent"
    elif any(k in query_lower for k in ["between", "across", "compare", "versus", "vs"]):
        has_comparison = True

    # 4. Requested attributes (units / target metrics)
    requested_attributes: list[str] = []
    attr_keywords = ["days", "months", "years", "percent", "amount", "dollars", "notice", "cap", "limit"]
    for attr in attr_keywords:
        if attr in query_lower:
            requested_attributes.append(attr)

    # If subtopic notice_period is present but no explicit unit requested
    if "notice_period" in subtopics and "days" not in requested_attributes:
        requested_attributes.append("days")
        requested_attributes.append("notice")

    # 5. Answer type
    answer_type = "cross_clause_comparison" if has_comparison else "single_clause_lookup"

    # Extract entities
    entities = extract_entities(query)

    return QueryIntent(
        topic=primary_topic,
        subtopics=subtopics,
        relationship=relationship_intent,
        entities=entities,
        requested_attributes=requested_attributes,
        answer_type=answer_type,
        has_comparison_intent=has_comparison,
    )
