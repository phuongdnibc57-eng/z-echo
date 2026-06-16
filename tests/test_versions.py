# tests/test_versions.py
from zecho import versions as v

def test_parse_version():
    assert v.parse_version("25.6.1") == (25, 6, 1)
    assert v.parse_version("25.6") == (25, 6)

def test_version_gt():
    assert v.version_gt("25.7.0", "25.6.1") is True
    assert v.version_gt("25.6.1", "25.6.1") is False
    assert v.version_gt("25.6", "25.6.1") is False

def test_newer_than_all():
    assert v.newer_than_all("25.7.0", ["25.6.0", "25.6.1"]) is True
    assert v.newer_than_all("25.6.1", ["25.6.0", "25.6.1"]) is False
    assert v.newer_than_all("25.6.0", ["25.6.1"]) is False
