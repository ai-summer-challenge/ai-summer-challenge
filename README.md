# PCF PDF Extractor

Python application scaffold for extracting Product Carbon Footprint information from supplier PDFs and preparing it for later API submission.

The target fields are:

- company name
- product name
- biogenic carbon content and fossil/non-biobased indication when relevant
- named minimum requirement checks with `fulfilled`, `result`, `evidence`, and `reason`

The minimum requirement checks are the source of truth for extracted requirement values. For example:

```json
{
  "minimum_requirements": {
    "gwp100": {
      "fulfilled": true,
      "result": {
        "value": 1.45,
        "unit": "kg CO2e/kg product"
      },
      "evidence": "PCF GWP 100 without biogenic carbon: 1.45 kg CO2e/kg product",
      "reason": "GWP 100 excluding biogenic carbon was extracted as a numeric value."
    },
    "production_location": {
      "fulfilled": true,
      "result": "US",
      "evidence": "Production location: US",
      "reason": "Production location found."
    }
  }
}
```

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

Extract structured records from a PDF:

```bash
pcf-extract extract data/incoming/example.pdf --output data/processed/example.json
```

If the PDF contains one chemical/product, this writes one JSON file. If the PDF contains
several chemicals/products, the app writes one JSON file per chemical. For example, with:

```bash
pcf-extract extract data/incoming/multi_product.pdf --output data/processed/multi_product.json
```

multi-product output is written to:

```text
data/processed/multi_product/
├── 01-first-product-name.json
└── 02-second-product-name.json
```

You can also pass a directory directly:

```bash
pcf-extract extract data/incoming/multi_product.pdf --output data/processed/multi_product/
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

Run the lightweight Streamlit review UI:

```bash
pip install -e ".[api,ui]"
uvicorn pcf_pdf_extractor.api.app:app --reload
```

In a second shell:

```bash
$env:BACKEND_API_URL="http://127.0.0.1:8000"
streamlit run frontend/streamlit_app.py
```

Or run the separated backend and frontend containers together:

```bash
docker compose up --build
```

The LLM extractor asks for a top-level `records` array and validates each item against the `PCFRecord` domain model before anything is exported or shipped. The heuristic extractor remains useful for tests, debugging, and cases where API access is not available.

Minimum requirement checks are generated for:

- PCF GWP 100 value excluding biogenic carbon
- PCF GWP 100 including biogenic carbon, unless the fossil/non-biobased exception applies
- system boundary
- accepted standard
- production location
- reference year
- impact assessment method
- secondary emission factor databases, limited to `ecoinvent 3.10` or `Sphera Managed Content 2024`
- whether `oil and gas update` is mentioned
- whether `ecoinvent 3.10` or `Sphera Managed Content 2024` is used as a secondary database; other secondary databases/versions fail the secondary database requirement
