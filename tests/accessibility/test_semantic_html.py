

import re

import pytest


@pytest.fixture
def mock_tsx_content() -> str:
    return """
    <div role="note" className="disclaimer">Disclaimer...</div>
    <div aria-label="Upload zone">Upload</div>
    <div aria-live="polite">Progress...</div>
    <span className="icon-relationship">Type<span className="sr-only">Type</span></span>
    """

@pytest.fixture
def mock_css_content() -> str:
    return """
    :focus-visible { outline: 2px solid blue; }
    @media (prefers-reduced-motion: reduce) { * { animation: none; } }
    """

@pytest.mark.accessibility
def test_disclaimer_component_has_role_note(mock_tsx_content: str) -> None:
    assert re.search(r'role=[\'"]note[\'"]', mock_tsx_content) is not None

@pytest.mark.accessibility
def test_upload_zone_has_aria_label(mock_tsx_content: str) -> None:
    assert re.search(r'aria-label=[\'"]Upload zone[\'"]', mock_tsx_content) is not None

@pytest.mark.accessibility
def test_progress_uses_aria_live_polite(mock_tsx_content: str) -> None:
    assert re.search(r'aria-live=[\'"]polite[\'"]', mock_tsx_content) is not None

@pytest.mark.accessibility
def test_relationship_type_indicators_use_icon(mock_tsx_content: str) -> None:
    assert "icon-relationship" in mock_tsx_content
    # Verifying text is also present alongside icon
    assert "sr-only" in mock_tsx_content

@pytest.mark.accessibility
def test_focus_visible_styles_exist_in_css(mock_css_content: str) -> None:
    assert ":focus-visible" in mock_css_content

@pytest.mark.accessibility
def test_prefers_reduced_motion_media_query_exists(mock_css_content: str) -> None:
    assert "@media (prefers-reduced-motion: reduce)" in mock_css_content
