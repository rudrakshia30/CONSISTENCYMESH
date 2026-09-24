"""
Documented threshold constants module for ConsistencyMesh matching.
"""
from backend.core.config import Settings


def get_threshold_documentation() -> dict[str, str]:
    """
    Returns documentation mapping for threshold parameters.

    Returns:
        A dictionary mapping threshold names to their descriptions.
    """
    return {
        "topic_weight": "Weight assigned to the topic overlap (Jaccard similarity) in the composite score. Typical Range: 0.0 to 1.0.",
        "entity_weight": "Weight assigned to the entity overlap (Jaccard similarity) in the composite score. Typical Range: 0.0 to 1.0.",
        "date_weight": "Weight assigned to the date overlap (Jaccard similarity) in the composite score. Typical Range: 0.0 to 1.0.",
        "tfidf_weight": "Weight assigned to the TF-IDF cosine similarity in the composite score. Typical Range: 0.0 to 1.0.",
        "composite_threshold": "The minimum composite score required for a clause pair to be considered a valid candidate. Typical Range: 0.0 to 1.0."
    }

def validate_thresholds(settings: Settings) -> list[str]:
    """
    Validates threshold values against expected ranges.

    Args:
        settings: The configuration settings object containing threshold values.

    Returns:
        A list of warning messages for any out-of-range values.
    """
    warnings = []

    # Expected bounds
    bounds = {
        "topic_weight": (0.0, 1.0),
        "entity_weight": (0.0, 1.0),
        "date_weight": (0.0, 1.0),
        "tfidf_weight": (0.0, 1.0),
        "composite_threshold": (0.0, 1.0)
    }

    for key, (min_val, max_val) in bounds.items():
        if hasattr(settings, key):
            val = getattr(settings, key)
            if not (min_val <= val <= max_val):
                warnings.append(f"Warning: {key} value ({val}) is outside the expected range [{min_val}, {max_val}].")

    # Validate sum of weights is close to 1.0
    weights = ["topic_weight", "entity_weight", "date_weight", "tfidf_weight"]
    total_weight = sum(getattr(settings, w, 0.0) for w in weights if hasattr(settings, w))

    if total_weight > 0 and abs(total_weight - 1.0) > 1e-4:
        warnings.append(f"Warning: The sum of the weights is {total_weight}, but it should ideally be 1.0.")

    return warnings
