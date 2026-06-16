# tests/test_priority.py
from zecho import priority as p

def test_severity_map():
    assert p.SEVERITY["high"] == 75
    assert p.SEVERITY["critical"] == 100

def test_compute_priority_bounds():
    score = p.compute_priority(impact=100, freq=50, segment=100, severity="critical")
    assert score == 100
    low = p.compute_priority(impact=0, freq=0, segment=0, severity="low")
    assert low == round(0.25 * 25)  # only severity contributes

def test_freq_capped():
    a = p.compute_priority(impact=0, freq=50, segment=0, severity="low")
    b = p.compute_priority(impact=0, freq=999, segment=0, severity="low")
    assert a == b  # freq capped at 50
