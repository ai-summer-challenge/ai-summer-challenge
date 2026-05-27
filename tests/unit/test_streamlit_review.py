from frontend.review import RecordReviewEdits, apply_record_review_edits


def test_apply_record_review_edits_updates_frontend_record_fields() -> None:
    record = {
        "company_name": "Old Co",
        "product_name": "Old Product",
        "minimum_requirements": {
            "gwp100": {
                "fulfilled": True,
                "result": {"value": 1.45, "unit": "kg CO2e/kg product"},
                "evidence": None,
                "reason": "Value found.",
            }
        },
    }

    reviewed = apply_record_review_edits(
        record,
        RecordReviewEdits(
            company_name="New Co",
            product_name="New Product",
            biogenic_carbon_content="0%",
            is_fossil_or_non_biobased_product=True,
            extraction_notes_text="Checked by reviewer\n\nReady for export",
        ),
    )

    assert reviewed["company_name"] == "New Co"
    assert reviewed["product_name"] == "New Product"
    assert reviewed["biogenic_carbon_content"] == "0%"
    assert reviewed["is_fossil_or_non_biobased_product"] is True
    assert reviewed["extraction_notes"] == ["Checked by reviewer", "Ready for export"]
    assert reviewed["minimum_requirements"] == record["minimum_requirements"]
