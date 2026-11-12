"""Tests for the CKD-EPI 2021 eGFR estimator and label-threshold extraction."""

from __future__ import annotations

import pytest

from app.core.egfr import egfr_ckd_epi_2021, extract_egfr_thresholds


def test_egfr_reference_vectors() -> None:
    assert egfr_ckd_epi_2021(30, "male", 1.0) == pytest.approx(103.8, abs=0.5)
    assert egfr_ckd_epi_2021(60, "female", 0.8) == pytest.approx(84.3, abs=0.5)
    assert egfr_ckd_epi_2021(60, "male", 1.0) == pytest.approx(86.2, abs=0.5)


def test_egfr_unit_conversion() -> None:
    # 88.4 umol/L == 1.0 mg/dL, so both units must agree.
    mg_dl = egfr_ckd_epi_2021(60, "male", 1.0, "mg_dl")
    umol = egfr_ckd_epi_2021(60, "male", 88.4, "umol_l")
    assert mg_dl == pytest.approx(umol, abs=0.01)


def test_egfr_input_bounds() -> None:
    with pytest.raises(ValueError):
        egfr_ckd_epi_2021(17, "male", 1.0)
    with pytest.raises(ValueError):
        egfr_ckd_epi_2021(121, "male", 1.0)
    with pytest.raises(ValueError):
        egfr_ckd_epi_2021(60, "male", 0.0)
    with pytest.raises(ValueError):
        egfr_ckd_epi_2021(60, "male", -1.0)


def test_extract_egfr_thresholds() -> None:
    text = (
        "Metformin is contraindicated in patients with an eGFR below 30 mL/min/1.73 m² "
        "and should not be initiated in patients with an eGFR between 30 and 45 mL/min/1.73 m²."
    )
    assert extract_egfr_thresholds(text) == [30.0, 45.0]


def test_extract_egfr_thresholds_ignores_unrelated_numbers() -> None:
    text = "Take one 500 mg tablet twice daily."
    assert extract_egfr_thresholds(text) == []
