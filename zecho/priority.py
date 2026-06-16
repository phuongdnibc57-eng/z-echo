# zecho/priority.py
SEVERITY = {"low": 25, "medium": 50, "high": 75, "critical": 100}
WEIGHTS = {"impact": 0.30, "freq": 0.30, "segment": 0.15, "severity": 0.25}

def compute_priority(impact: float, freq: int, segment: float, severity: str,
                     weights: dict = WEIGHTS) -> int:
    freq_norm = min(freq, 50) / 50 * 100
    sev = SEVERITY[severity]
    score = (weights["impact"] * impact
             + weights["freq"] * freq_norm
             + weights["segment"] * segment
             + weights["severity"] * sev)
    return round(score)
