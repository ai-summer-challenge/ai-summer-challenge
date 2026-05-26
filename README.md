# PCF PDF Extractor

Python application scaffold for extracting Product Carbon Footprint information from supplier PDFs and preparing it for later API submission.

The target fields are:

- company name
- product name
- PCF GWP 100 values with and without biogenic carbon
- biogenic carbon content and fossil/non-biobased indication when relevant
- unit
- system boundary, for example `cradle-to-gate`
- standards used, for example TfS, ISO 14040, ISO 14044, ISO 14067
- product location
- reference year of data collection
- impact assessment method, for example IPCC AR6 or CML2001
- secondary emission factor databases and versions
- per-criterion minimum requirement checks with `fulfilled`, `evidence`, and `reason`

## Project Tree

```text
.
├── data/
│   ├── incoming/        # Local PDFs, not intended for version control
│   └── processed/       # Local extracted JSON files
├── docs/
│   └── architecture.md
├── src/
│   └── pcf_pdf_extractor/
│       ├── application/ # Use cases
│       ├── domain/      # PCF data model and validation
│       ├── extraction/  # Extraction strategies
│       └── infrastructure/
│           ├── api/     # Outbound company API client
│           ├── llm/     # LLM API client
│           └── pdf/     # PDF text reader
└── tests/
    └── unit/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Usage

Extract a structured record from a PDF:

```bash
pcf-extract extract data/incoming/example.pdf --output data/processed/example.json
```

LLM extraction is the default. Configure it in `.env` first:

```bash
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-me
LLM_MODEL=replace-with-your-model
```

For an offline first pass, use the heuristic extractor:

```bash
pcf-extract extract data/incoming/example.pdf --extractor heuristic --output data/processed/example.json
```

Ship a reviewed record to the configured company API:

```bash
pcf-extract ship data/processed/example.json
```

The LLM extractor validates model output against the `PCFRecord` domain model before anything is exported or shipped. The heuristic extractor remains useful for tests, debugging, and cases where API access is not available.

Minimum requirement checks are generated for:

- PCF GWP 100 values
- system boundary
- accepted standard
- production location
- reference year
- impact assessment method
- secondary emission factor databases and versions
