from datetime import date, timedelta

import pytest

from validation import check_transaction_date, clean_text


def test_clean_text_trims_and_collapses_whitespace():
    assert clean_text("  Grocery   shopping \n", field="x", max_length=50) == "Grocery shopping"


@pytest.mark.parametrize("bad", ["", "   ", "abc\x00def", "a\x07b"])
def test_clean_text_rejects_empty_and_control_chars(bad):
    with pytest.raises(ValueError):
        clean_text(bad, field="x", max_length=50)


def test_clean_text_rejects_too_long():
    with pytest.raises(ValueError):
        clean_text("a" * 51, field="x", max_length=50)


def test_clean_text_allows_empty_when_requested():
    assert clean_text("  ", field="x", max_length=5, allow_empty=True) == ""


def test_sql_injection_text_is_kept_as_plain_text():
    payload = "'; DROP TABLE users; --"
    assert clean_text(payload, field="x", max_length=50) == payload


def test_date_bounds():
    assert check_transaction_date(date.today()) == date.today()
    with pytest.raises(ValueError):
        check_transaction_date(date(1999, 12, 31))
    with pytest.raises(ValueError):
        check_transaction_date(date.today() + timedelta(days=400))
