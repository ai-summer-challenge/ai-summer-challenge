# Architecture

The application is organized around a single workflow:

1. Read a supplier PDF.
2. Extract raw text while preserving page boundaries.
3. Convert that text into one `PCFRecord` per distinct chemical/product, preferably with an LLM extractor.
4. Store required extracted values under `minimum_requirements.<field>.result`.
5. Assess each extracted record against the minimum supplier-documentation requirements.
6. Validate and review the extracted data.
7. Export one JSON file per chemical/product, or submit reviewed records to an external API.

## Layers

- `domain`: stable business objects such as `PCFRecord`, `MinimumRequirements`, and `SecondaryDatabase`.
- `domain/minimum_requirements.py`: deterministic assessment of the minimum requirements.
- `application`: use cases that coordinate domain objects and adapters.
- `extraction`: extraction strategies. The default implementation is LLM-backed; a heuristic extractor remains available as a fallback.
- `infrastructure/pdf`: PDF reading adapters.
- `infrastructure/llm`: LLM API clients.
- `infrastructure/api`: outbound API clients.

## Notes for the next iteration

- Add OCR for scanned PDFs before LLM extraction.
- Add confidence scores and field-level source page references.
- Add a reference-data comparison layer for chemical identifiers and expected GWP values.
- Add a human review screen or validation report before records are shipped.
- Add a real API contract once the receiving company's endpoint is known.
