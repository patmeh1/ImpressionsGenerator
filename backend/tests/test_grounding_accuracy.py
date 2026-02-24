"""Grounding accuracy test suite – verifies no hallucinated clinical data
appears in generated output.  Tests the *actual* ``validate_grounding``
service so that regressions are caught automatically on every PR.
"""

from app.services.grounding import GroundingResult, validate_grounding


# ── helpers ──────────────────────────────────────────────────────────────────

def _assert_grounded(result: GroundingResult) -> None:
    """Shorthand: the result must be fully grounded (no hallucinations)."""
    assert result.is_grounded, (
        f"Expected grounded output but found hallucinated values: "
        f"{result.hallucinated_values}"
    )
    assert result.hallucinated_values == []


def _assert_not_grounded(result: GroundingResult) -> None:
    """Shorthand: the result must flag hallucinations."""
    assert not result.is_grounded, "Expected hallucinated output to be flagged"
    assert len(result.hallucinated_values) > 0


# ── known inputs with specific measurements (cm) ────────────────────────────

class TestMeasurementPreservation:
    """Feed known inputs and verify numbers are preserved exactly."""

    def test_cm_mass_preserved(self):
        inp = "CT chest: 3.2 cm mass in right upper lobe."
        out = "A 3.2 cm mass is present in the right upper lobe."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_mm_nodule_preserved(self):
        inp = "A 6 mm pulmonary nodule noted in the left lower lobe."
        out = "There is a 6 mm nodule in the left lower lobe."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_multiple_cm_measurements(self):
        inp = (
            "Right kidney 11.2 cm. Left kidney 10.8 cm. "
            "Spleen 12.1 cm. Aorta 2.3 cm."
        )
        out = (
            "Right kidney measures 11.2 cm. Left kidney 10.8 cm. "
            "Spleen is 12.1 cm. Aorta caliber 2.3 cm."
        )
        result = validate_grounding(inp, out)
        _assert_grounded(result)
        assert len(result.missing_from_output) == 0


# ── various measurement types ───────────────────────────────────────────────

class TestVariousMeasurementTypes:
    """cm, mm, mL, mg, %, Hounsfield units, SUV values."""

    def test_ml_volume(self):
        inp = "Pleural effusion estimated at 250 mL on the right."
        out = "Right-sided pleural effusion approximately 250 mL."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_mg_dosage(self):
        inp = "Patient received 100 mg contrast."
        out = "100 mg of contrast was administered."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_percentage_stenosis(self):
        inp = "Left ICA stenosis estimated at 70%."
        out = "Approximately 70% stenosis of the left ICA."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_hounsfield_units(self):
        inp = "Adrenal nodule measures 15 HU on non-contrast CT."
        out = "The adrenal nodule has attenuation of 15 HU."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_suv_values(self):
        inp = "FDG-avid lesion with SUVmax of 8.5 SUV."
        out = "The lesion demonstrates avid uptake, 8.5 SUV."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_mixed_units_single_report(self):
        inp = (
            "Lung mass 4.1 cm with 45 HU attenuation. "
            "Pleural effusion 300 mL. Stenosis 60%."
        )
        out = (
            "A 4.1 cm lung mass with attenuation of 45 HU. "
            "Pleural effusion measuring 300 mL. Stenosis approximately 60%."
        )
        result = validate_grounding(inp, out)
        _assert_grounded(result)


# ── dates ────────────────────────────────────────────────────────────────────

class TestDatesPreserved:
    """Verify dates in input are not altered in output."""

    def test_iso_date(self):
        inp = "Compared to prior study 2024-01-15, mass is unchanged."
        out = "Stable compared to 2024-01-15 examination."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_us_date_format(self):
        inp = "Prior CT from 03/22/2023 shows a 2.1 cm nodule."
        out = "Compared to 03/22/2023, the 2.1 cm nodule is unchanged."
        result = validate_grounding(inp, out)
        _assert_grounded(result)


# ── patient ages ─────────────────────────────────────────────────────────────

class TestPatientAges:
    """Verify patient age numbers are preserved."""

    def test_age_preserved(self):
        inp = "72-year-old male with cough. 3.2 cm mass in RUL."
        out = "72-year-old male. 3.2 cm right upper lobe mass."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_age_not_hallucinated(self):
        inp = "Elderly male with cough. 3.2 cm mass in RUL."
        out = "75-year-old male. 3.2 cm right upper lobe mass."
        result = validate_grounding(inp, out)
        _assert_not_grounded(result)


# ── lesion counts ────────────────────────────────────────────────────────────

class TestLesionCounts:
    """Verify lesion counts are preserved accurately."""

    def test_lesion_count_preserved(self):
        inp = "There are 7 hepatic lesions identified."
        out = "7 hepatic lesions are noted."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_lesion_count_hallucinated(self):
        inp = "There are 7 hepatic lesions identified."
        out = "12 hepatic lesions are noted."
        result = validate_grounding(inp, out)
        _assert_not_grounded(result)


# ── edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge-case scenarios for grounding validation."""

    def test_no_measurements_input_none_in_output(self):
        """No measurements in input → verify none appear in output."""
        inp = "The liver appears normal. No focal lesion identified."
        out = "The liver is unremarkable. No focal lesion is seen."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_no_measurements_input_hallucinated_output(self):
        """No measurements in input but output invents a measurement."""
        inp = "The liver appears normal."
        out = "The liver measures 14.5 cm and appears normal."
        result = validate_grounding(inp, out)
        _assert_not_grounded(result)

    def test_decimal_precision_preserved(self):
        """Decimal precision must be exact – 3.2 ≠ 3.20 in raw text."""
        inp = "Mass measures 3.2 cm."
        out = "A 3.2 cm mass is identified."
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_empty_input_empty_output(self):
        result = validate_grounding("", "")
        _assert_grounded(result)

    def test_hallucinated_number_detected(self):
        """Output introduces a number not present in input."""
        inp = "Mass measures 3.2 cm."
        out = "A 3.2 cm mass. Additional 1.5 cm satellite nodule."
        result = validate_grounding(inp, out)
        _assert_not_grounded(result)


# ── multiple measurements in a single report ────────────────────────────────

class TestMultipleMeasurements:
    """Reports with many measurements — all must be preserved."""

    def test_complex_report_all_preserved(self):
        inp = (
            "Right kidney 11.2 cm. Left kidney 10.8 cm. "
            "Liver 16.3 cm. Spleen 12.1 cm. Aorta 2.3 cm. "
            "Gallbladder wall 3 mm. CBD 4 mm."
        )
        out = (
            "Right kidney measures 11.2 cm, left kidney 10.8 cm. "
            "The liver span is 16.3 cm; spleen 12.1 cm. "
            "Aorta caliber 2.3 cm. Gallbladder wall is 3 mm. "
            "Common bile duct measures 4 mm."
        )
        result = validate_grounding(inp, out)
        _assert_grounded(result)
        assert len(result.missing_from_output) == 0

    def test_mixed_measurement_types_all_preserved(self):
        inp = (
            "Lung nodule 8 mm. Pleural effusion 200 mL. "
            "Ejection fraction 55%. Lesion SUVmax 6.2 SUV. "
            "Adrenal density 10 HU. Contrast dose 120 mg."
        )
        out = (
            "8 mm lung nodule. Pleural effusion of 200 mL. "
            "EF is 55%. Lesion SUVmax 6.2 SUV. "
            "Adrenal density 10 HU. 120 mg contrast administered."
        )
        result = validate_grounding(inp, out)
        _assert_grounded(result)

    def test_partial_preservation_flags_missing(self):
        inp = "Mass 3.2 cm. Lymph node 1.5 cm. Effusion 100 mL."
        out = "Mass 3.2 cm. Lymph node not well seen."
        result = validate_grounding(inp, out)
        # 1.5 cm and 100 mL are missing — should be flagged in missing_from_output
        assert len(result.missing_from_output) > 0
