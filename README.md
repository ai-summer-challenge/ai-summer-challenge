# PCF PDF Extractor

Python application scaffold for extracting Product Carbon Footprint information from supplier documents and preparing it for later API submission.

The target fields are:

- source file
- raw text SHA-256
- company name
- product name
- expected GWP 100 value from the BAFU reference data, when mapped
- Oil & Gas relevance from the Eclasses reference file, when mapped
- named minimum requirement checks with `fulfilled`, `result`, `evidence`, and `reason`
- extraction notes

The minimum requirement checks are the source of truth for extracted requirement values. For example:

```json
{
  "source_file": "data/incoming/example.pdf",
  "raw_text_sha256": "abc123...",
  "company_name": "Example Chemicals",
  "product_name": "Solvent X",
  "expected_gwp100_value": {
    "value": 1.75,
    "unit": "kg CO2 eq/kg"
  },
  "oil_gas_relevant": true,
  "minimum_requirements": {
    "gwp100_excluding_biogenic": {
      "fulfilled": true,
      "result": {
        "value": 1.45,
        "unit": "kg CO2e/kg product"
      },
      "evidence": "PCF GWP 100 without biogenic carbon: 1.45 kg CO2e/kg product",
      "reason": "GWP 100 excluding biogenic carbon was extracted with value and unit."
    },
    "gwp100_including_biogenic": {
      "fulfilled": false,
      "result": null,
      "evidence": null,
      "reason": "No GWP 100 including biogenic carbon value with unit was extracted."
    },
    "production_location": {
      "fulfilled": true,
      "result": "US",
      "evidence": "Production location: US",
      "reason": "Production location of the product/process found."
    }
  },
  "extraction_notes": []
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
├── resources/           # BAFU extract, Eclasses list, and mapping prompt
├── src/
│   └── pcf_pdf_extractor/
│       ├── application/ # Use cases
│       ├── domain/      # PCF data model and validation
│       ├── enrichment/  # BAFU/Eclasses reference-data enrichment
│       ├── extraction/  # Extraction strategies
│       └── infrastructure/
│           ├── api/     # Outbound company API client
│           ├── llm/     # LLM API client
│           ├── pdf/     # Backward-compatible PDF reader wrapper
│           └── source/  # PDF, Excel, and email-body readers
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

Supported input formats:

- PDF: `.pdf`
- Excel: `.xlsx`, `.xlsm`, `.xltx`, `.xltm`, `.xls`
- Email body only: `.eml`, `.msg`, `.mail`

Email attachments are intentionally ignored. If a supplier sends an Excel or PDF attachment, process that attachment as its own input file.

Extract structured records from a source file:

```bash
pcf-extract extract data/incoming/example.pdf --output data/processed/example.json
```

To run extraction and then immediately enrich each JSON with the BAFU expected GWP 100
value and Eclasses Oil & Gas relevance:

```bash
pcf-extract extract data/incoming/example.pdf --enrich-reference-data --output data/processed/example.json
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

A small script is also available if you want a direct extension-based file-to-JSON entry point:

```bash
python scripts/extract_source_to_json.py data/incoming/example.xlsx --output data/processed/example.json
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

Enrich an already extracted JSON:

```bash
pcf-extract enrich data/processed/example.json --output data/processed/example.enriched.json
```

The enrichment step uses `resources/prompt_mapping.txt` with candidate BAFU rows from
`resources/BAFU Extract.xlsx` and the full `resources/EclasseswithOilGasRelevance.txt`
list. If the BAFU row is ambiguous, `expected_gwp100_value` remains `null` and an
extraction note is added.

Ship a reviewed record to the configured company API:

```bash
pcf-extract ship data/processed/example.json
```

The LLM extractor asks for a top-level `records` array and validates each item against the `PCFRecord` domain model before anything is exported or shipped. The heuristic extractor remains useful for tests, debugging, and cases where API access is not available.

Minimum requirement checks are generated for:

- PCF GWP 100 value excluding biogenic carbon
- PCF GWP 100 including biogenic carbon when reported
- system boundary
- accepted standard
- production location of the product/process, not the report issuer
- reference year of the production data/data collection, not the report year
- impact assessment method
- secondary emission factor databases, limited to `ecoinvent 3.10` or `Sphera Managed Content 2024`
