from pydantic import BaseModel, ConfigDict, Field, field_validator


class PcfValueResult(BaseModel):
    """Numeric PCF value and its unit."""

    model_config = ConfigDict(extra="forbid")

    value: float
    unit: str = Field(
        description="Unit attached to the PCF value, for example kg CO2e/kg product."
    )


class SecondaryDatabase(BaseModel):
    """A secondary emission factor database cited by the source document."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str | None = None


class BaseRequirementCheck(BaseModel):
    """Assessment of one minimum supplier-documentation requirement."""

    model_config = ConfigDict(extra="forbid")

    fulfilled: bool
    evidence: str | None = Field(
        default=None,
        description="Short evidence from the supplier documentation, ideally with page marker.",
    )
    reason: str = Field(description="Why the criterion is fulfilled or not fulfilled.")


class PcfValueRequirementCheck(BaseRequirementCheck):
    result: PcfValueResult | None = None


class TextRequirementCheck(BaseRequirementCheck):
    result: str | None = None


class YearRequirementCheck(BaseRequirementCheck):
    result: int | None = None

    @field_validator("result")
    @classmethod
    def result_must_be_reasonable_year(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1990 or value > 2100:
            raise ValueError("result must be between 1990 and 2100")
        return value


class BooleanRequirementCheck(BaseRequirementCheck):
    result: bool | None = None


class StandardsRequirementCheck(BaseRequirementCheck):
    result: list[str] = Field(default_factory=list)


class SecondaryDatabasesRequirementCheck(BaseRequirementCheck):
    result: list[SecondaryDatabase] = Field(default_factory=list)


class MinimumRequirements(BaseModel):
    """Named checklist of minimum supplier-documentation requirements."""

    model_config = ConfigDict(extra="forbid")

    gwp100_excluding_biogenic: PcfValueRequirementCheck = Field(
        description="Mandatory GWP 100 value excluding biogenic carbon."
    )
    gwp100_including_biogenic: PcfValueRequirementCheck = Field(
        description="GWP 100 value including biogenic carbon, when reported."
    )
    system_boundary: TextRequirementCheck
    accepted_standard: StandardsRequirementCheck
    production_location: TextRequirementCheck
    reference_year: YearRequirementCheck
    impact_assessment_method: TextRequirementCheck
    secondary_databases: SecondaryDatabasesRequirementCheck
    oil_and_gas_update: BooleanRequirementCheck


class PCFRecord(BaseModel):
    """Structured data expected from a supplier PCF source document."""

    model_config = ConfigDict(extra="forbid")

    source_file: str | None = None
    raw_text_sha256: str | None = None

    company_name: str | None = None
    product_name: str | None = None
    minimum_requirements: MinimumRequirements
    extraction_notes: list[str] = Field(default_factory=list)


class PCFExtractionResult(BaseModel):
    """One extraction run, potentially containing several chemical/product records."""

    model_config = ConfigDict(extra="forbid")

    records: list[PCFRecord] = Field(
        description="One PCF record per distinct chemical/product in the supplier documentation."
    )
