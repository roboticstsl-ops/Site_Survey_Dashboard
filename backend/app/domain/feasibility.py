"""Same rule as the phone app's computeFeasibility()/verdictOf() in
mobile/www/index.html — kept identical on purpose (BUILD_SPEC section 2.4 /
section 11: server derives feasibility from valid filled cells, same rule).
"""
from __future__ import annotations

Verdict = str  # "Good" | "Acceptable" | "Poor" | ""


def verdict_of(avg_rsrp: float | None, avg_sinr: float | None) -> Verdict:
    if avg_rsrp is None:
        return ""
    sinr = 20.0 if avg_sinr is None else avg_sinr
    if avg_rsrp >= -90 and sinr >= 12:
        return "Good"
    if avg_rsrp >= -105 and sinr >= 5:
        return "Acceptable"
    return "Poor"


def average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize_cells(cells: dict[str, float | str], carrier: str) -> dict:
    """cells uses the flat '<row>|<carrier>.<metric>' key format. Returns the
    per-metric averages + verdict for one carrier, matching avgBlock() in the
    phone app."""
    metrics = ("rsrp", "rsrq", "sinr", "dl", "ul", "ping")
    buckets: dict[str, list[float]] = {m: [] for m in metrics}
    for key, value in cells.items():
        for m in metrics:
            if key.endswith(f"{carrier}.{m}"):
                try:
                    buckets[m].append(float(value))
                except (TypeError, ValueError):
                    pass
    avgs = {m: average(v) for m, v in buckets.items() if v}
    return {
        "averages": {k: round(v, 1) for k, v in avgs.items()},
        "verdict": verdict_of(avgs.get("rsrp"), avgs.get("sinr")),
    }
