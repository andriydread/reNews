import json

from app.models.models import ArticleCategory
from app.services.ai_processor import AIProcessor

VALID_ENTRY = {
    "id": 1,
    "summary": "Something happened.",
    "category": "Science & Space",
    "language": "English",
}


def _reply(entries) -> str:
    return json.dumps(entries)


def test_parse_reply_valid_array():
    results = AIProcessor()._parse_reply(_reply([VALID_ENTRY]), expected_ids={1})
    assert results[1].category == ArticleCategory.SCIENCE
    assert results[1].summary == "Something happened."


def test_parse_reply_tolerates_fences_and_prose():
    raw = "Here you go:\n```json\n" + _reply([VALID_ENTRY]) + "\n```\nDone!"
    results = AIProcessor()._parse_reply(raw, expected_ids={1})
    assert set(results) == {1}


def test_parse_reply_skips_invalid_entries():
    bad_category = {**VALID_ENTRY, "id": 2, "category": "Not A Category"}
    missing_field = {"id": 3, "summary": "no category or language"}
    raw = _reply([VALID_ENTRY, bad_category, missing_field])
    results = AIProcessor()._parse_reply(raw, expected_ids={1, 2, 3})
    assert set(results) == {1}


def test_parse_reply_drops_hallucinated_ids():
    stray = {**VALID_ENTRY, "id": 999}
    results = AIProcessor()._parse_reply(_reply([VALID_ENTRY, stray]), expected_ids={1})
    assert set(results) == {1}


def test_parse_reply_no_array_returns_empty():
    assert AIProcessor()._parse_reply("Sorry, I cannot help.", expected_ids={1}) == {}


def test_build_prompt_lists_articles_and_categories():
    prompt = AIProcessor()._build_prompt([(7, "Title 7", "Body 7"), (8, "T8", "B8")])
    assert "article id: 7" in prompt
    assert "article id: 8" in prompt
    for category in ArticleCategory:
        assert category.value in prompt
