"""Metadata extraction utilities including deterministic numeric attribute parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.models.schemas import NumericAttribute


@dataclass
class MetadataResult:
    entities: list[str]
    dates: list[str]
    monetary_values: list[str]
    topics: list[str]
    numeric_attributes: list[NumericAttribute]


WORD_TO_NUM: dict[str, float] = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "fifteen": 15.0,
    "twenty": 20.0,
    "thirty": 30.0,
    "forty": 40.0,
    "fifty": 50.0,
    "sixty": 60.0,
    "seventy": 70.0,
    "eighty": 80.0,
    "ninety": 90.0,
    "one hundred": 100.0,
}


def parse_number_value(text_val: str) -> float | None:
    """Parse string number (digits or English word) into float."""
    clean_val = text_val.strip().lower()
    if clean_val.isdigit():
        return float(clean_val)
    try:
        return float(clean_val.replace(",", ""))
    except ValueError:
        pass
    return WORD_TO_NUM.get(clean_val, None)


def extract_numeric_attributes(text: str) -> list[NumericAttribute]:
    """Extract structured numerical attributes (durations, caps, percentages).

    Args:
        text: Input clause text.

    Returns:
        List of extracted NumericAttribute instances.
    """
    results: list[NumericAttribute] = []
    text_lower = text.lower()

    # Pattern for durations: "ninety (90) days", "30 days", "fifteen (15) days", "12 months"
    duration_pattern = re.compile(
        r"\b((?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety))\s*(?:\((\d+)\)\s*)?(days?|months?|years?|business days?|calendar days?)\b",
        re.IGNORECASE,
    )

    for match in duration_pattern.finditer(text):
        raw_full = match.group(0)
        word_part = match.group(1)
        parentheses_part = match.group(2)
        unit = match.group(3).lower()

        val: float | None = None
        if parentheses_part and parentheses_part.isdigit():
            val = float(parentheses_part)
        else:
            val = parse_number_value(word_part)

        if val is not None:
            # Attribute category classification
            attr_cat = "duration"
            if "notice" in text_lower or "terminate" in text_lower or "cancellation" in text_lower:
                attr_cat = "notice_period"
            elif "due" in text_lower or "payment" in text_lower or "invoice" in text_lower:
                attr_cat = "payment_term"
            elif "renew" in text_lower or "extension" in text_lower:
                attr_cat = "renewal_period"
            elif "retain" in text_lower or "retention" in text_lower or "storage" in text_lower:
                attr_cat = "retention_period"

            results.append(
                NumericAttribute(
                    attribute=attr_cat,
                    value=val,
                    unit=unit,
                    raw_text=raw_full,
                )
            )

    # Pattern for monetary caps/amounts: "$150,000", "USD 1,000,000"
    money_pattern = re.compile(
        r"(?:\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)|(?:USD|EUR|GBP)\s*(\d+(?:,\d{3})*(?:\.\d+)?))",
        re.IGNORECASE,
    )
    for match in money_pattern.finditer(text):
        raw_full = match.group(0)
        val_str = match.group(1) or match.group(2)
        val = parse_number_value(val_str)
        if val is not None:
            attr_cat = "amount"
            if "liability" in text_lower or "cap" in text_lower or "maximum" in text_lower:
                attr_cat = "liability_cap"
            results.append(
                NumericAttribute(
                    attribute=attr_cat,
                    value=val,
                    unit="USD",
                    raw_text=raw_full,
                )
            )

    return results


def extract_entities(text: str) -> list[str]:
    """Extracts proper nouns and company-like names from text."""
    pattern = r'\b(?:[A-Z][a-zA-Z]*\s+)+(?:[A-Z][a-zA-Z]*|(?:Inc\.?|LLC|Corp\.?|Ltd\.?|Company|Association|Partners))\b|\b[A-Z][a-zA-Z]*\s+(?:Inc\.?|LLC|Corp\.?|Ltd\.?|Company|Association|Partners)\b|\"(?:[A-Z][a-zA-Z]*\s*)+\"'
    matches = re.findall(pattern, text)
    return list(set([m.strip(' "') for m in matches if len(m.strip(' "')) > 3]))


def extract_dates(text: str) -> list[str]:
    """Extracts date patterns from text."""
    pattern = r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|within\s+\d+\s+(?:days?|months?|years?))\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return list(set([m.strip() for m in matches]))


def extract_monetary_values(text: str) -> list[str]:
    """Extracts monetary values from text."""
    pattern = r'(?:\$\s*\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s+(?:dollars|USD|EUR|GBP)\b|\b(?:USD|EUR|GBP)\s+\d+(?:,\d{3})*(?:\.\d{2})?\b)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return list(set([m.strip() for m in matches]))


def extract_topics(text: str) -> list[str]:
    """Assigns topics from a fixed vocabulary based on keyword presence."""
    topic_map = {
        'termination': ['terminate', 'termination', 'end of agreement', 'cancellation'],
        'payment': ['pay', 'payment', 'fee', 'invoice', 'compensation', 'remuneration', 'due fifteen', 'receipt'],
        'liability': ['liability', 'liable', 'damages', 'limitation of liability'],
        'indemnification': ['indemnify', 'indemnification', 'hold harmless', 'defend'],
        'confidentiality': ['confidential', 'confidentiality', 'non-disclosure', 'nda'],
        'intellectual_property': ['intellectual property', 'ip rights', 'trademark', 'copyright', 'patent'],
        'warranty': ['warranty', 'warranties', 'warrant', 'as is'],
        'insurance': ['insurance', 'insured', 'policy', 'coverage'],
        'notice': ['notice', 'notices', 'notify', 'written notice'],
        'governing_law': ['governing law', 'jurisdiction', 'applicable law', 'choice of law'],
        'dispute_resolution': ['dispute', 'arbitration', 'mediation', 'resolve'],
        'force_majeure': ['force majeure', 'act of god', 'unforeseeable'],
        'assignment': ['assign', 'assignment', 'transfer'],
        'amendment': ['amend', 'amendment', 'modify', 'modification'],
        'term_duration': ['term', 'duration', 'effective date', 'commencement', 'retention', 'renewal'],
        'scope_of_work': ['scope of work', 'services', 'deliverables', 'statement of work'],
        'compliance': ['comply', 'compliance', 'applicable laws', 'regulations'],
        'data_protection': ['data protection', 'privacy', 'gdpr', 'ccpa', 'personal data'],
        'non_compete': ['non-compete', 'non-solicitation', 'compete'],
        'representations': ['represent', 'representations', 'warrant and represent']
    }
    found_topics = []
    text_lower = text.lower()
    for topic, keywords in topic_map.items():
        if any(kw in text_lower for kw in keywords):
            found_topics.append(topic)
    return found_topics


def extract_metadata(text: str) -> MetadataResult:
    """Extracts all metadata from a text string."""
    return MetadataResult(
        entities=extract_entities(text),
        dates=extract_dates(text),
        monetary_values=extract_monetary_values(text),
        topics=extract_topics(text),
        numeric_attributes=extract_numeric_attributes(text),
    )
