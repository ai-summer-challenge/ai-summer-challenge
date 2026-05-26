from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Gwp100Values(BaseModel):
    """GWP 100 values reported for one Product Carbon Footprint."""

    model_config = ConfigDict(extra="forbid")

    with_biogenic_carbon: float | None = Field(
        default=None,
        description="PCF GWP 100 value including biogenic carbon, when reported.",
    )
    without_biogenic_carbon: float | None = Field(
        default=None,
        description="PCF GWP 100 value excluding biogenic carbon, when reported.",
    )
    unit: str | None = Field(
        default=None,
        description="Unit attached to the PCF value, for example kg CO2e/kg product.",
    )


class SecondaryDatabase(BaseModel):
    """A secondary emission factor database cited by the source document."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str | None = None


RequirementCriterionId = Literal[
    "pcf_gwp100_values",
    "system_boundary",
    "accepted_standard",
    "production_location",
    "reference_year",
    "impact_assessment_method",
    "secondary_databases",
]


class MinimumRequirementCheck(BaseModel):
    """Assessment of one minimum supplier-documentation requirement."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: RequirementCriterionId
    criterion: str
    fulfilled: bool
    evidence: str | None = Field(
        default=None,
        description="Short evidence from the supplier documentation, ideally with page marker.",
    )
    reason: str = Field(description="Why the criterion is fulfilled or not fulfilled.")


class PCFRecord(BaseModel):
    """Structured data expected from a supplier PCF PDF."""

    model_config = ConfigDict(extra="forbid")

    source_file: str | None = None
    raw_text_sha256: str | None = None

    company_name: str | None = None
    product_name: str | None = None
    biogenic_carbon_content: str | None = Field(
        default=None,
        description="Reported biogenic carbon content, for example 0%, when available.",
    )
    is_fossil_or_non_biobased_product: bool | None = Field(
        default=None,
        description=(
            "Whether the document indicates the product is fossil or not biobased. "
            "This supports the one-PCF-value exception."
        ),
    )
    gwp100: Gwp100Values = Field(default_factory=Gwp100Values)
    system_boundary: str | None = Field(
        default=None,
        description="System boundary used for PCF calculation, for example cradle-to-gate.",
    )
    standards: list[str] = Field(default_factory=list)
    product_location: str | None = Field(
        default=None,
        description="Country or region where the product/process data applies.",
    )
    reference_year: int | None = Field(
        default=None,
        description="Reference year for data collection.",
    )
    impact_assessment_method: str | None = Field(
        default=None,
        description="Impact assessment method used, for example IPCC AR6 or CML2001.",
    )
    secondary_databases: list[SecondaryDatabase] = Field(default_factory=list)
    minimum_requirements: list[MinimumRequirementCheck] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)

    @field_validator("reference_year")
    @classmethod
    def reference_year_must_be_reasonable(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1990 or value > 2100:
            raise ValueError("reference_year must be between 1990 and 2100")
        return value
