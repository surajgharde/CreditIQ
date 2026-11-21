"""
Label matching in the OCR layer.

The short-acronym and currency-normalisation patterns in ocr_service were
written as r'^H...' — a literal backspace byte (0x08) rather than the word
boundary r'\b' that was meant. A backspace never appears in extracted text, so
every pattern that used it could not match: EBIT, COGS, NPAT and PAT were never
read, and "Rs"/"INR" were never normalised to the rupee sign. These tests pin
the boundary behaviour so the byte cannot creep back in.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ocr_service import clean_indian_numbers, find_financial_indicators


def _indicators(text: str) -> dict:
    indicators, _confidence = find_financial_indicators(text)
    return indicators


def test_ebit_label_is_read():
    assert _indicators("EBIT 1,200")["ebit"] == 1200


def test_ebitda_does_not_fill_ebit():
    indicators = _indicators("EBITDA 1,500")
    assert indicators.get("ebitda") == 1500
    assert "ebit" not in indicators


def test_ebit_and_ebitda_on_separate_lines_keep_their_own_amounts():
    indicators = _indicators("EBITDA 1,500\nEBIT 1,200")
    assert indicators["ebitda"] == 1500
    assert indicators["ebit"] == 1200


@pytest.mark.parametrize(
    "label,key,expected",
    [
        ("COGS 3,400", "cogs", 3400),
        ("NPAT 950", "net_profit", 950),
        ("PAT 870", "net_profit", 870),
    ],
)
def test_short_acronyms_are_read(label, key, expected):
    assert _indicators(label)[key] == expected


def test_currency_prefixes_are_normalised():
    assert clean_indian_numbers("Rs. 1,200").startswith("₹")
    assert clean_indian_numbers("INR 1,200").startswith("₹")


def test_currency_normalisation_does_not_corrupt_ordinary_words():
    # "rs" inside "Shareholders" must not be treated as a currency token.
    for word in ("Shareholders", "creditors", "debtors", "directors", "borrowers"):
        assert word.lower() in clean_indian_numbers(word).lower()
        assert "₹" not in clean_indian_numbers(word)


def test_no_backspace_bytes_remain_in_ocr_service():
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "services",
        "ocr_service.py",
    )
    with open(path, "rb") as fh:
        assert b"\x08" not in fh.read()
