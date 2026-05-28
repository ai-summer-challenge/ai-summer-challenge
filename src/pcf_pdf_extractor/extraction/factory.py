from enum import StrEnum

from pcf_pdf_extractor.config import Settings
from pcf_pdf_extractor.extraction.base import PcfExtractor
from pcf_pdf_extractor.extraction.heuristic_extractor import HeuristicPcfExtractor
from pcf_pdf_extractor.extraction.llm_pcf_extractor import LlmPcfExtractor
from pcf_pdf_extractor.infrastructure.llm import ChatCompletionsLlmClient


class ExtractorKind(StrEnum):
    LLM = "llm"
    HEURISTIC = "heuristic"


def build_extractor(kind: ExtractorKind, settings: Settings) -> PcfExtractor:
    if kind == ExtractorKind.HEURISTIC:
        return HeuristicPcfExtractor()
    if kind == ExtractorKind.LLM:
        return LlmPcfExtractor(
            client=ChatCompletionsLlmClient.from_settings(settings),
            max_input_chars=settings.llm_max_input_chars,
            system_prompt_path=settings.extraction_system_prompt_path,
            user_prompt_path=settings.extraction_user_prompt_path,
        )
    raise ValueError(f"Unsupported extractor kind: {kind}")
