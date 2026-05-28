from pcf_pdf_extractor.config import Settings
from pcf_pdf_extractor.enrichment.reference_data import ReferenceDataEnricher
from pcf_pdf_extractor.infrastructure.llm import ChatCompletionsLlmClient


def build_reference_data_enricher(settings: Settings) -> ReferenceDataEnricher:
    return ReferenceDataEnricher.from_paths(
        client=ChatCompletionsLlmClient.from_settings(settings),
        bafu_path=settings.reference_bafu_extract_path,
        oil_gas_path=settings.reference_oil_gas_eclasses_path,
        prompt_path=settings.reference_mapping_prompt_path,
        candidate_limit=settings.reference_mapping_candidate_limit,
    )
