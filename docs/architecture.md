# Architecture

The application is organized around a single workflow:

1. Read a supplier PDF.
2. Extract raw text while preserving page boundaries.
3. Convert that text into a structured `PCFRecord`, preferably with an LLM extractor.
4. Assess the extracted data against the minimum supplier-documentation requirements.
5. Validate and review the extracted data.
6. Export or submit the record to an external API.

## Layers

- `domain`: stable business objects such as `PCFRecord`, `Gwp100Values`, and `SecondaryDatabase`.
- `domain/minimum_requirements.py`: deterministic assessment of the minimum requirements.
- `application`: use cases that coordinate domain objects and adapters.
- `extraction`: extraction strategies. The default implementation is LLM-backed; a heuristic extractor remains available as a fallback.
- `infrastructure/pdf`: PDF reading adapters.
- `infrastructure/llm`: LLM API clients.
- `infrastructure/api`: outbound API clients.

## Notes for the next iteration

- Add OCR for scanned PDFs before LLM extraction.
- Add confidence scores and field-level source page references.
- Add a human review screen or validation report before records are shipped.
- Add a real API contract once the receiving company's endpoint is known.
