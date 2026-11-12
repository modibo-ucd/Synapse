"""CKD-EPI 2021 (race-free) eGFR estimation and label-threshold extraction."""

from __future__ import annotations

import re
from typing import Literal

Sex = Literal["male", "female"]
CreatinineUnit = Literal["mg_dl", "umol_l"]

_UMOL_PER_MGDL = 88.4
_EGFR_KEYWORD = re.compile(r"egfr|glomerular filtration rate", re.IGNORECASE)
_BELOW_RE = re.compile(r"(?:below|less than|under|<)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_BETWEEN_RE = re.compile(
    r"between\s*(\d+(?:\.\d+)?)\s*(?:and|to|[-–])\s*(\d+(?:\.\d+)?)", re.IGNORECASE
)


def egfr_ckd_epi_2021(
    age: int,
    sex: Sex,
    serum_creatinine: float,
    creatinine_unit: CreatinineUnit = "mg_dl",
) -> float:
    """Estimate GFR with the CKD-EPI 2021 creatinine equation (race-free).

    ``serum_creatinine`` is interpreted in ``creatinine_unit`` (``mg_dl`` or
    ``umol_l``). Inputs are bounded; out-of-range values raise ``ValueError``.
    """
    if not 18 <= age <= 120:
        raise ValueError("age must be between 18 and 120")
    if serum_creatinine <= 0:
        raise ValueError("serum creatinine must be positive")

    scr = serum_creatinine / _UMOL_PER_MGDL if creatinine_unit == "umol_l" else serum_creatinine
    if not 0.1 <= scr <= 20:
        raise ValueError("serum creatinine out of range (0.1–20 mg/dL)")

    kappa = 0.7 if sex == "female" else 0.9
    alpha = -0.241 if sex == "female" else -0.302
    ratio = scr / kappa
    egfr: float = 142.0 * min(ratio, 1.0) ** alpha * max(ratio, 1.0) ** -1.200 * 0.9938**age
    if sex == "female":
        egfr *= 1.012
    return float(round(egfr, 1))


def extract_egfr_thresholds(text: str) -> list[float]:
    """Extract eGFR numeric thresholds mentioned in a label passage.

    Only numbers that appear in an eGFR/glomerular-filtration context are kept;
    duplicates are removed and the result is sorted ascending.
    """
    if not _EGFR_KEYWORD.search(text):
        return []

    values: list[float] = []
    for match in _BELOW_RE.finditer(text):
        window = text[max(0, match.start() - 100) : match.end() + 100]
        if _EGFR_KEYWORD.search(window):
            values.append(float(match.group(1)))
    for match in _BETWEEN_RE.finditer(text):
        window = text[max(0, match.start() - 100) : match.end() + 100]
        if _EGFR_KEYWORD.search(window):
            values.append(float(match.group(1)))
            values.append(float(match.group(2)))

    deduped: list[float] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return sorted(deduped)
