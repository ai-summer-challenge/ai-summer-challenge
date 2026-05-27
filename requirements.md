# Requirements: Supplier PCF Review Assistant

## 1. Purpose

Build a prototype assistant for reviewing supplier-provided Product Carbon Footprint (PCF) documentation. The first project phase focuses on Priority 1 from the proposal: supplier PCF extraction, Evonik minimum requirement checks, benchmark plausibility checks, and an explainable review summary.

The solution should reduce manual review effort, improve consistency, improve
data accuracy, and provide transparent evidence for acceptance, rejection, or
human follow-up decisions.

## 2. Background

Supplier PCFs arrive in inconsistent formats such as PDFs, Excel forms, and text-based documents. Reviewers currently need to manually extract PCF values and metadata, check whether the documentation satisfies Evonik minimum requirements, and judge whether reported PCF values are plausible compared with public benchmarks.

The prototype must demonstrate that this workflow can be automated in a transparent, reproducible way. It does not need to be a production enterprise system.

## 3. Users and Stakeholders

Primary users:

- Life Cycle Management (LCM)
- Sustainability Procurement
- Evonik Carbon Footprint team

Secondary stakeholders:

- Business lines that consume supplier PCF data
- Suppliers, indirectly, through feedback on missing or insufficient documentation

Stakeholder priorities clarified in the Evonik feedback meeting:

- The primary value driver is reviewer time savings, because the current task is
  not conceptually hard but is repetitive and easy to misread or overlook.
- Data accuracy and validation quality are equally important because automation
  should reduce the frequency of manual checking errors.
- The business case is tied to cheaper, faster PCF review and more reliable
  supplier data quality.
- External auditability matters: reviewers need documentation of what was
  checked, what evidence was used, and why a decision or follow-up was produced.

## 4. Scope

### 4.1 In Scope for First Phase

- Ingest supplier PCF files from the local repository.
- Support structured Excel supplier PCF forms first.
- Support text extraction from supplier PCF PDFs and EPD-style PDFs after the Excel workflow is proven.
- Extract PCF values and required metadata into a canonical data model.
- Check extracted data against Evonik minimum PCF data requirements.
- Check oil-and-gas update relevance where applicable.
- Compare supplier PCF values against at least one public or provided benchmark source.
- Flag benchmark deviations above 30 percent.
- Generate a human-readable review summary with evidence, missing fields, confidence, and recommended decision.

### 4.2 Out of Scope for First Phase

- Full ISO-compliant LCA modelling.
- Priority 2 chemical PCF estimator.
- Creating proprietary emission factor databases.
- Enterprise authentication, permissions, or deployment.
- Handling confidential supplier data beyond the anonymized/synthetic examples in the repository.
- Impact categories other than climate change / GWP100.

## 5. Core User Workflow

1. User selects or uploads supplier PCF documents, commonly in batches.
2. System classifies the document type, for example Excel PCF form, PDF supplier report, EPD, SDS, guideline, or unrelated LCA document.
3. System extracts relevant PCF fields and metadata.
4. System normalizes extracted data into a canonical PCF review record.
5. System checks the record against Evonik minimum requirements.
6. System checks whether the product or raw material is oil-and-gas sensitive.
7. System checks whether the product appears in the relevant comparison dataset
   or internal reference export before performing the benchmark comparison.
8. System compares the supplier PCF value to benchmark or reference emission
   factors.
9. System produces a review result: accepted, rejected, or needs human review.
10. User inspects extracted values, evidence, missing fields, confidence notes,
    benchmark comparison, and prior review history.
11. User can use the result as a first-pass supplier PCF screening output and as
    documentation for later follow-up or audit requests.

## 6. Canonical PCF Review Record

The system shall normalize extracted data into a common structure with at least the following fields:

- `source_file`
- `document_type`
- `supplier_name`
- `product_name`
- `declared_unit`
- `declared_quantity`
- `product_mass_kg_per_declared_unit`
- `system_boundary`
- `pcf_excl_biogenic_kg_co2e`
- `pcf_incl_biogenic_kg_co2e`
- `biogenic_carbon_content`
- `geography`
- `reference_period_start`
- `reference_period_end`
- `reference_year`
- `date_of_issue`
- `validity_period_end`
- `calculation_standard`
- `product_or_sector_rule`
- `impact_assessment_method`
- `secondary_database_and_version`
- `attestation_or_certificate`
- `oil_and_gas_relevance`
- `oil_and_gas_update_status`
- `benchmark_source`
- `benchmark_dataset_name`
- `benchmark_value_kg_co2e`
- `benchmark_deviation_percent`
- `requirements_status`
- `plausibility_status`
- `overall_decision`
- `confidence`
- `evidence`
- `review_run_id`
- `review_timestamp`
- `supplier_follow_up_question`
- `human_review_reason`
- `comparison_dataset_presence`
- `decision_comment`
- `top_match_candidate`
- `match_uncertainty_comment`

## 7. Functional Requirements

### 7.1 Document Ingestion and Classification

- The system shall discover supplier documents in the repository data directory.
- The system shall distinguish supplier PCF documents from supporting references such as SDS files, guidelines, certificates, and benchmark datasets.
- The system shall prioritize structured Excel PCF forms for the first working prototype.
- The system should support PDF text extraction for supplier PCF reports and EPD documents after the Excel workflow is complete.
- The system shall preserve the source file path for traceability.
- The system should support batch processing of 100 to 200 supplier files per
  run, because Evonik currently processes roughly 600 to 700 supplier documents
  per year and expects this volume to grow.
- The system shall support the common case of one chemical per supplier document
  and the less common case where one supplier document contains multiple
  chemicals.

### 7.2 Data Extraction

- The system shall extract product name, supplier name, declared unit, declared quantity, and product mass where available.
- The system shall extract PCF values excluding biogenic carbon.
- The system shall extract PCF values including biogenic carbon where available.
- The system shall extract biogenic carbon content where available.
- The system shall extract the system boundary, such as cradle-to-gate.
- The system shall extract geography or production location.
- The system shall extract reference period, reference year, date of issue, and validity date where available.
- The system shall extract applied calculation standards.
- The system shall extract impact assessment method, such as IPCC AR6.
- The system shall extract secondary emission factor databases and versions.
- The system shall extract attestation or certificate information where available.
- The system shall retain evidence for each extracted value, such as row label, cell location, page number, or text snippet.

### 7.3 Normalization

- The system shall normalize PCF values to `kg CO2e / kg product` where the declared unit and quantity make this possible.
- The system shall preserve original units and values when normalization is uncertain.
- The system shall normalize accepted standards into a consistent internal representation.
- The system shall normalize common product names sufficiently to support benchmark and oil-and-gas relevance matching.
- The system shall mark fields as missing, present, inferred, or uncertain.

### 7.4 Minimum Requirement Checks

The system shall check supplier documentation against the following minimum requirements:

- A PCF value excluding biogenic emissions and removals is provided.
- A PCF value including biogenic emissions and removals is provided when applicable.
- For fossil or non-biobased products with zero biogenic carbon content, a single PCF value excluding biogenic carbon is sufficient.
- The system boundary is provided.
- The applied calculation standard is provided.
- The applied standard is accepted when it is in line with TfS guideline, ISO 14040/14044, or ISO 14067.
- The production location, country, region, or geography is provided.
- The reference year or reference period of data collection is provided.
- The impact assessment method is provided.
- Secondary emission factor databases and versions are provided.
- The oil-and-gas sector update requirement is checked when the product or raw material is oil-and-gas sensitive.

Each check shall return one of:

- `pass`
- `fail`
- `missing`
- `not_applicable`
- `uncertain`

### 7.5 Oil-and-Gas Update Check

- The system shall use the provided oil-and-gas relevance list as the first relevance source.
- If the product or raw material is not on the oil-and-gas relevance list, the oil-and-gas update check shall be marked `not_applicable`.
- If the product or raw material is oil-and-gas sensitive, the system shall check whether the documentation states that the oil-and-gas update was included.
- The system shall treat use of `ecoinvent 3.10` or `Sphera Managed Content 2024` as satisfying the oil-and-gas update requirement unless contradictory evidence is present.
- If relevance is detected but update status cannot be proven, the system shall flag the criterion as `missing` or `uncertain`.

### 7.6 Benchmark Plausibility Check

- The system shall use the provided BAFU benchmark extract as the first benchmark source.
- The system shall attempt to match supplier products to benchmark rows using product name and relevant aliases.
- The system shall preserve the selected benchmark source, matched benchmark name, unit, region, and GWP100 value.
- The system shall calculate the percent deviation between supplier PCF and benchmark value.
- The system shall flag deviations greater than 30 percent as significant.
- The system shall mark benchmark results as uncertain when the product match, unit, concentration, region, or production route is ambiguous.
- The system shall flag when no exact benchmark or reference match is found and
  provide close match suggestions for human decision during trial use.
- When benchmark or reference matching is uncertain, the system shall still show
  the top match candidate, its match confidence or rationale, and a clear
  uncertainty comment.
- The system shall not average regional reference values. When regional
  benchmark or internal database values exist, the system shall preserve the
  specific region and compare against the relevant regional value.
- The system shall check whether the chemical exists in the relevant comparison
  dataset or internal reference export before final plausibility comparison.
- The system shall flag unusually low or high PCF values as plausibility issues
  even when minimum documentation requirements are otherwise complete.

### 7.7 Review Decision

- The system shall produce an overall decision for each supplier document.
- The allowed decisions shall be:
  - `accept`
  - `reject`
  - `needs_human_review`
- The system shall recommend `accept` only when all mandatory requirements pass or are not applicable, and no significant unexplained benchmark deviation is found.
- The system shall recommend `reject` when mandatory data is clearly missing or a mandatory requirement clearly fails.
- The system shall recommend `needs_human_review` when extraction, benchmark matching, oil-and-gas relevance, or plausibility is uncertain.
- The system shall never hide uncertainty behind an acceptance decision.

### 7.8 Reporting

- The system shall generate a review report with one row or section per supplier product.
- The report shall include extracted PCF values, requirement check results, oil-and-gas status, benchmark comparison, deviation percent, overall decision, confidence, and evidence.
- The report shall clearly show missing fields.
- The report shall clearly separate automated findings from inferred or uncertain findings.
- The report shall provide a concise comment for each final decision, including
  why a record was accepted, rejected, or marked as needing human review.
- The report shall provide comments for missing information and uncertain
  findings so reviewers can understand the required next action.
- The MVP report shall prioritize a detailed Excel-compatible output because
  stakeholders value a traceable working file more than a polished dashboard.
- The report should be exportable as Excel or CSV first, with Markdown, HTML, or
  local web views as secondary presentation formats.
- The report shall include one column for each minimum requirement check, one
  column showing whether the requirement is fulfilled, and one column showing
  the supplier-provided value or `not_given`.
- The report should include comments such as values being close to a limit,
  uncertain, missing, or deviating from expectations.
- The report shall highlight uncertain benchmark/reference matching by showing
  the best available match candidate while clearly marking that the match is not
  confirmed.
- The report shall support trace-back to the source document evidence so a human
  reviewer can double-check a result against the original supplier file.
- The report should include a concise supplier follow-up summary and, where
  useful, a copy/paste-ready supplier email question for missing or unclear
  information.

### 7.9 Human-AI Interaction

- The system shall behave as an explainable review assistant, not a black-box judge.
- The system shall show the user why each criterion passed, failed, or needs review.
- The system shall provide enough evidence for a human reviewer to validate or override the result.
- The system should support user correction of extracted values or benchmark matches in later iterations.
- The system should minimize manual work for clearly structured documents while escalating ambiguous cases.
- The system shall return unclear or close-match cases to humans instead of
  forcing a false exact match.
- The system shall indicate whether missing information should trigger supplier
  follow-up, and should formulate the missing information as a specific question
  when possible.
- The system shall generate decision comments that are understandable without
  re-reading the full source document, especially for accept, reject, missing
  data, and uncertain match outcomes.

## 8. Non-Functional Requirements

### 8.1 Transparency

- All decisions shall be traceable to extracted data, source evidence, or explicit rule logic.
- The system shall avoid unexplained black-box decisions.

### 8.2 Reproducibility

- Given the same input files and benchmark data, the system shall produce the same review results.
- Rule versions and benchmark source versions should be visible in the report.

### 8.3 Modularity

- Extraction logic shall be separate from validation logic.
- Benchmark matching shall be separate from minimum requirement checks.
- New document formats should be addable through adapters.
- New benchmark sources should be addable without rewriting validation rules.

### 8.4 Usability

- The first prototype shall be usable without enterprise setup.
- The workflow shall be simple enough for a reviewer to understand: select document, review extracted values, inspect flags, export result.
- Output shall use plain language suitable for sustainability and procurement users.
- A website-style prototype is acceptable, but the first screen should support
  practical file upload/review work rather than a fancy dashboard.
- The interface should make it easy to see which documents have already been
  checked and which remain unresolved.
- A detailed Excel-compatible result is more important than dashboard polish for
  the first phase.

### 8.5 Scalability and Expandability

- The architecture shall support additional supplier formats, benchmark sources, and rule sets.
- The architecture should support future integration of the Priority 2 PCF estimator.
- The system should support batch review of multiple supplier documents,
  including 100 to 200 files in one run for the target stakeholder workflow.

### 8.6 Data Constraints

- The system shall use only public, anonymized, synthetic, or locally provided non-confidential data.
- The system shall not require proprietary emission factor databases for the first prototype.
- The system should be designed so Evonik can later replace or supplement public
  benchmark data with exports from its internal Sphera-based database or Excel
  reference files.
- The first prototype should treat an Excel export of internal reference data as
  a likely future integration point.

### 8.7 Review History and Auditability

- The system shall preserve a review history for generated results so reviewers
  can inspect what was checked during a prior run.
- Review history should support later investigation when an error is discovered
  months after the original review.
- Review history should be suitable as supporting documentation for external
  audits.
- Each review run should store input file identity, extracted values, rule
  results, benchmark/reference matches, decision, confidence, and evidence.

## 9. Initial Data Sources

Primary challenge documents:

- `data/01_Proposal.pdf`
- `data/2026_Minimum requirements for PCF data_suppliers.pdf`
- `data/Eclasses with Oil & Gas Relevance.pdf`
- `data/BAFU Extract.xlsx`
- `data/TfS-PCF-Guidelines-2024.pdf`

Initial supplier PCF examples:

- `data/Supplier 1_POLYGLYKOL 600.xlsx`
- `data/Supplier 2_N-Butyl Alcohol.xlsx`
- `data/Supplier 3_Methanol.xlsx`
- `data/Supplier 4_Acetic Acid.xlsx`
- `data/Supplier 5_Phenol PCF.pdf`
- `data/Supplier 6_NaOH50.pdf`

Secondary and later-phase examples:

- Supplier EPD PDFs
- Supplier LCA reports
- Safety Data Sheets
- `data/List of proxies requested.xlsx`
- `data/03_Sphera Dataset List MLC Databases 2025.2 Edition.xlsx`

## 10. MVP Acceptance Criteria

The first working MVP is acceptable when it can:

- Parse the four structured supplier Excel PCF forms.
- Produce one normalized PCF review record per Excel file.
- Run all minimum requirement checks listed in this document.
- Detect whether oil-and-gas update handling is applicable or missing for matched products.
- Match at least N-Butyl Alcohol, Acetic Acid, Phenol, and Sodium Hydroxide examples to plausible BAFU benchmark candidates where present.
- Calculate and flag benchmark deviations above 30 percent.
- Generate a human-readable report with extracted values, rule results, benchmark comparison, decision, confidence, and evidence.
- Clearly mark uncertain or missing information instead of silently accepting it.
- Produce a detailed Excel-compatible output that can be used as the main review
  artifact.
- Show which documents or chemicals have already been checked in the current
  run, and preserve enough history for later trace-back.
- When no exact benchmark/reference match exists, flag the issue and provide
  close match suggestions for human review.
- For uncertain benchmark/reference matches, show the top match candidate and
  highlight why the match remains uncertain.
- Generate a concise summary of missing or deviating information and a
  supplier-facing follow-up question where appropriate.

## 11. Success Metrics

The prototype should be judged against the challenge scoring criteria as follows:

### 11.1 Quality of Overall Output

- The solution directly addresses supplier PCF review.
- The output includes extraction, compliance checking, plausibility assessment, and a decision summary.
- Results are evidence-backed and reproducible.

### 11.2 Quality of AI-Human Interaction

- The assistant explains each finding.
- The assistant distinguishes facts, inferred values, missing data, and uncertainty.
- The workflow supports human review rather than replacing domain judgment blindly.

### 11.3 User Engagement

- The user workflow is straightforward.
- The report is readable by sustainability procurement and LCM users.
- The prototype demonstrates practical organizational value.

### 11.4 Immediate Usability

- The first version works on existing repository examples.
- The solution can deliver value before PDF parsing is perfect.
- The output can be used as a first-pass review checklist.

### 11.5 Scalability and Expandability

- The system uses a canonical schema and modular adapters.
- Additional file formats, benchmarks, and rule sets can be added.
- The same architecture can later support the PCF estimator and other carbon-data quality workflows.

## 12. Key Design Principles

- Separate extraction from judgment.
- Prefer deterministic rules for compliance decisions.
- Preserve evidence for every important value.
- Escalate uncertainty to human review.
- Start with the highest-value structured documents.
- Keep the prototype transparent, local, and reproducible.
- Prefer detailed, traceable Excel outputs over visual dashboard polish in the
  MVP.
- Preserve region-specific comparison values instead of averaging reference data.
- Keep humans in control of close matches, missing data, and plausibility
  outliers.
- Keep `prompt.md` aligned with `requirements.md` when requirements or workflow
  decisions affect Spec Kit prompts.

## 13. Open Questions for Later Specification

- What exact UI form should the first prototype use: CLI, notebook, local web app, or Streamlit-style dashboard?
- Should human corrections be stored, and if so, in which format?
- Which benchmark source should be authoritative when multiple matches exist?
- How strict should acceptance be when benchmark matching is uncertain?
- Should PDF extraction use deterministic parsing only, or allow an LLM-assisted extraction step with evidence validation?
- Which companion demo view is useful alongside the Excel-first output: local
  web app, Markdown, or HTML?

## 14. Challenge Assessment and Work Pillars

Based on the available challenge documents and sample data, the work should be
organized into four pillars:

### 14.1 Pillar 1: Document Intake and Evidence Extraction

Challenge: supplier PCF evidence arrives in mixed formats, including structured
Excel forms, supplier PCF PDFs, EPDs, SDS files, certificates, benchmark
spreadsheets, and guideline PDFs. The first implementation must prioritize the
structured supplier Excel forms while preserving a path to PDF and EPD support.

Required focus:

- Discover and classify repository files by role and document type.
- Parse structured Excel PCF forms into a canonical record.
- Preserve source evidence for extracted values, including row labels, cells,
  pages, or snippets.
- Mark missing, uncertain, inferred, and present fields explicitly.
- Avoid treating supporting documents such as SDSs or certificates as supplier
  PCF declarations.

### 14.2 Pillar 2: PCF Data Quality and Minimum Requirement Validation

Challenge: supplier PCF submissions must be checked against Evonik minimum
requirements, but submissions vary in completeness and terminology. Missing
mandatory fields, incomplete standard references, missing impact assessment
methods, stale database versions, or unclear biogenic carbon handling must be
surfaced transparently.

Required focus:

- Implement deterministic rule checks for mandatory PCF data requirements.
- Validate PCF values excluding biogenic carbon and, where applicable, including
  biogenic carbon.
- Check system boundary, geography, reference period/year, standards, product or
  sector rules, impact assessment method, secondary database/version, and
  attestation information.
- Treat accepted standards such as TfS, ISO 14040/14044, and ISO 14067
  consistently.
- Escalate uncertainty rather than allowing uncertain records to pass silently.

### 14.3 Pillar 3: Plausibility, Benchmarking, and Oil-and-Gas Relevance

Challenge: a valid-looking PCF can still be implausible or incomplete for the
product context. Product names must be matched to benchmark and relevance data
despite aliases, chemistry naming differences, units, regions, concentrations,
and production routes.

Required focus:

- Match supplier products to the BAFU benchmark extract using product names and
  aliases.
- Normalize supplier PCF values to kg CO2e per kg product when possible.
- Calculate benchmark deviation and flag deviations above 30 percent.
- Preserve benchmark source, matched dataset name, unit, region, and confidence.
- Add a dataset-presence quality check before final benchmark comparison.
- Suggest close benchmark/reference matches when no exact match is available,
  and route the decision to a human reviewer.
- Preserve region-specific reference values rather than averaging regional data.
- Apply the oil-and-gas relevance list and check update status for relevant
  products.
- Treat ecoinvent 3.10 or Sphera Managed Content 2024 as satisfying the
  oil-and-gas update criterion unless contradictory evidence is found.

### 14.4 Pillar 4: Explainable Review Output and Human Workflow

Challenge: the assistant must support expert review rather than act as an
opaque accept/reject engine. Sustainability, procurement, and carbon-footprint
reviewers need concise outputs that explain what was found, what is missing,
why a decision was recommended, and where human judgment is still required.

Required focus:

- Produce one review result per supplier product with accept, reject, or
  needs_human_review.
- Include extracted values, requirement statuses, benchmark comparison,
  oil-and-gas status, confidence, and evidence.
- Separate automated findings from inferred or uncertain findings.
- Generate a detailed Excel-compatible report as the primary MVP output, with
  CSV, Markdown, HTML, or a local UI view as secondary formats.
- Preserve run history and evidence so reviewers can later trace decisions for
  audits or error investigation.
- Generate supplier-facing follow-up questions for missing or unclear data
  where possible.
- Keep the first prototype local, reproducible, and usable without enterprise
  setup.

## 15. Input and Output Inventory

The repository currently contains input documents and reference material, but no
finished example output report has been identified.

### 15.1 Primary Inputs for the MVP

These files are supplier PCF declarations to be parsed and reviewed:

- `data/Supplier 1_POLYGLYKOL 600.xlsx`
- `data/Supplier 1_Propylene Oxide.xlsx`
- `data/Supplier 2_N-Butyl Alcohol.xlsx`
- `data/Supplier 3_Methanol.xlsx`
- `data/Supplier 4_Acetic Acid.xlsx`
- `data/Supplier 5_Phenol PCF.pdf`
- `data/Supplier 6_NaOH50.pdf`

The Excel files are the first-priority MVP inputs. The supplier PDF files are
later or secondary extraction inputs after the Excel flow is working.

### 15.2 Reference Inputs

These files provide rules, benchmark data, relevance data, or background
context used to evaluate supplier declarations:

- `data/01_Proposal.pdf`
- `data/2026_Minimum requirements for PCF data_suppliers.pdf`
- `data/TfS-PCF-Guidelines-2024.pdf`
- `data/BAFU Extract.xlsx`
- `data/Eclasses with Oil & Gas Relevance.pdf`
- `data/List of proxies requested.xlsx`
- `data/03_Sphera Dataset List MLC Databases 2025.2 Edition.xlsx`
- `data/Evonik TÜV Certification.pdf`

### 15.3 Secondary or Later-Phase Inputs

These files are useful for future PDF classification, EPD extraction, SDS
handling, proxy matching, or broader LCA-document support, but they are not the
first MVP target:

- Supplier EPD PDFs under `data/`
- Supplier LCA report PDFs under `data/`
- Safety Data Sheet PDFs under `data/`
- Other supplier report PDFs under `data/`

### 15.4 Expected Output

The expected output is a generated review report, not currently present as an
example artifact. It should contain one row or section per supplier product with
the normalized PCF review record, minimum requirement check results,
oil-and-gas relevance status, benchmark match, deviation percent, evidence,
confidence, and overall decision.

The first preferred output format is an Excel-compatible detailed review file.
It should be easy for reviewers to filter, inspect, trace back, and use as audit
documentation. A website or local web prototype can be used for upload and
review, but the Excel-compatible output remains the main MVP artifact.

## 16. Stakeholder Alignment Presentation

For the Evonik alignment meeting, the presentation should primarily demonstrate
that the team understands the supplier PCF review problem, the reviewer workflow,
the available inputs, the required checks, and the expected human-review output.
The meeting should lead with the problem framing and workflow before showing
technical implementation details.

## 17. Evonik Feedback Incorporated on 2026-05-26

The Evonik feedback clarified that the most time-consuming current activity is
manual checking across two sources: the minimum requirements and the supplier
data. The task is repetitive rather than technically difficult, and reviewers can
miss details when reading manually. The prototype should therefore emphasize time
savings, fewer checking errors, and transparent validation.

Updated requirements from the feedback:

- Primary stakeholder value is time efficiency, followed closely by data
  accuracy, quality validation, and audit-ready documentation.
- Current annual volume is approximately 600 to 700 supplier documents, expected
  to increase. Batch runs of 100 to 200 files should be supported.
- The normal case is one chemical per supplier document, but some documents may
  include up to around 10 chemicals and should produce multiple review rows.
- A website-style prototype is acceptable for upload and review, but the MVP
  should focus on detailed Excel-compatible output rather than dashboard polish.
- Users need to see what has already been checked and later trace an error back
  to the original evidence, including for external audits.
- If no exact benchmark or reference match exists, the system should flag the
  missing match and suggest close candidates for human review.
- If matching is uncertain, the system should show the top match candidate and a
  visible uncertainty comment instead of hiding the match or treating it as
  confirmed.
- Reference comparisons must preserve regional values. The system should not
  average multiple regional PCF values into a single comparison value.
- If required supplier information is missing, the output should explain whether
  the requirement is fulfilled, why not, and what specific question should be
  sent back to the supplier.
- The workflow needs an additional quality check between extraction/validation
  and final comparison: confirm whether the chemical exists in the other dataset
  or reference export before relying on a benchmark comparison.

## 18. Spec Kit Workflow Prompt Management

The project will use the GitHub Spec Kit approach for at least the first
implementation task. `prompt.md` shall store reusable prompts for Spec Kit
workflow commands, starting with constitution and specify.

Prompt management requirements:

- `prompt.md` shall be updated when requirements change in a way that affects
  Spec Kit constitution, specification, planning, task, or implementation
  prompts.
- The constitution prompt shall encode project principles around time savings,
  evidence-backed transparency, human-in-the-loop review, deterministic checks,
  audit-ready history, Excel-first reporting, and scoped MVP extensibility.
- The specify prompt shall describe the Supplier PCF Review Assistant feature in
  product terms, focusing on what and why rather than implementation details.
- `requirements.md` remains the source of truth; `prompt.md` is the operational
  prompt companion derived from it.

## 19. Technical Solution Direction

The current technical scaffold is documented in `technical-solution.md`. It is a
planning artifact for Spec Kit and future implementation work.

Architecture direction:

- Build the MVP as a local-first web workbench connected to a Python processing
  backend.
- Use multi-file upload as the first ingestion mode; treat cloud-folder or
  watched-folder ingestion as a later extension.
- Use deterministic scripts for intake, classification of known file types,
  structured Excel extraction, normalization, minimum requirement checks,
  benchmark/reference calculations, decision logic, and Excel report generation.
- Use LLMs or agents as controlled document-understanding helpers when they add
  value for messy PDFs, scanned documents, inconsistent workbook layouts,
  ambiguous extraction, close-match suggestions, uncertainty explanation,
  decision-comment drafting, supplier follow-up wording, or audit summaries.
- Determinism is required most strongly at the schema, validation, rule,
  calculation, decision, and report-generation layers. Raw text/table extraction
  may use deterministic tools, OCR, or LLM/agent-assisted methods if the output
  is stored with evidence, tool/model metadata, and uncertainty flags.
- The LLM/agent shall never be the final authority for accept/reject decisions;
  final decisions remain deterministic and evidence-backed.
- The website should behave as a review workbench with run history, batch
  upload, stage progress, a detailed review grid, evidence inspection, and
  Excel-compatible export.
- The first persistence layer can be local filesystem plus typed JSON artifacts;
  add SQLite when the website needs run-history/filtering APIs, and move to
  PostgreSQL/object storage later if cloud or multi-user operation is needed.
- Agentic workflows should be connected through backend job orchestration and
  stage-level status updates, not direct uncontrolled browser-to-agent calls.
- The first agentic implementation should stay minimal: use one explicit
  workflow coordinator or pipeline orchestrator that can call deterministic
  tools and a small number of schema-constrained specialist agent functions.
- Initial specialist agent roles should be limited to extraction assistance,
  benchmark/reference match suggestion, reviewer comment drafting, supplier
  follow-up wording, and audit summary drafting.
- Separate persona agents should not be introduced unless a specific workflow
  need appears. For the MVP, domain personas such as LCA expert, procurement
  reviewer, or auditor should be represented as task instructions or prompt
  context rather than independent agents.
- Shared agent instructions may be kept in small versioned files such as
  `agents/skills.md` and `agents/commands.md` when this reduces prompt drift,
  but these files should remain minimal and subordinate to `requirements.md`,
  `prompt.md`, and typed schemas.
- Deterministic scripts/modules should own repeatable state-changing workflow
  steps: intake, hashing, known Excel extraction, normalization, requirement
  checks, benchmark calculations, decision logic, and report generation.
- Agent commands/skills should be used only for repeatable language-reasoning
  tasks: messy document field mapping, unknown workbook layout interpretation,
  close-match rationale, reviewer comment drafting, supplier follow-up wording,
  and audit summaries. Their outputs must be schema-validated and evidence-bound.

File and schema decisions:

- It is acceptable and preferred to start with Excel/CSV files as the first
  reference-data source for benchmarks and internal exports.
- Excel/CSV shall be treated as input/export formats, not the only internal
  state format for extracted data.
- Scraped or extracted data from PDFs and other sources should be stored as
  typed JSON artifacts with evidence metadata; Markdown may be generated only as
  a human-readable companion or debug preview.
- The project shall define explicit schemas for canonical records, requirement
  checks, evidence references, benchmark/reference match candidates, decisions,
  and final report rows before populating CSV/XLSX outputs.
- The final Excel/CSV output shall be generated from a stable report-row schema
  so columns remain predictable across runs.

## 20. Task 1 Supplier PCF Proposal Coverage

Task 1 from the proposal is the primary MVP scope. All specification, planning,
implementation, and reporting work must optimize for the supplier PCF review
workflow before expanding into Task 2 estimator work or other challenge ideas.

### 20.1 Task 1 Objective

The solution must help reviewers process supplier-provided PCF information,
extract the relevant PCF values and metadata, validate the submission against
Evonik minimum requirements, compare the supplier result against benchmark or
reference data, and produce a transparent review output that supports accept,
reject, or human follow-up decisions.

The goal is not to build a full LCA model. The goal is a first-pass supplier
PCF quality review assistant that reduces repetitive review effort while keeping
expert judgment, evidence, and auditability visible.

### 20.2 Task 1 Input Coverage

The MVP shall treat `data/01_Task` as the Task 1 input corpus. The proposal
states that supplier exchange formats may include PDF, Excel, text, and PPT;
the first MVP prioritizes Excel and PDF while preserving explicit extension
points for text/email and PPT-derived supplier submissions. The solution shall
explicitly support or classify these input groups:

- Structured supplier PCF Excel forms:
  - `Supplier 1_Propylene Oxide.xlsx`
  - `Supplier 1_POLYGLYKOL 600.xlsx`
  - `Supplier 2_N-Butyl Alcohol.xlsx`
  - `Supplier 3_Methanol.xlsx`
  - `Supplier 4_Acetic Acid.xlsx`
- Supplier PCF or LCA PDF examples:
  - `Supplier 5_Phenol PCF.pdf`
  - `Supplier 6_NaOH50.pdf`
  - `Supplier_*.pdf`
  - supplier LCA/report PDFs in `data/01_Task`
- EPD PDFs in `data/01_Task`, which should be classified and handled as
  secondary or later-phase supplier evidence unless they contain directly
  extractable PCF/GWP100 data.
- Reference and rule sources:
  - `BAFU Extract.xlsx` as the first benchmark/reference source.
  - `Eclasses with Oil & Gas Relevance.pdf` as the first oil-and-gas relevance
    source.
  - `TfS-PCF-Guidelines-2024.pdf` as standards and terminology context.
- Public benchmark sources mentioned by the proposal, such as openLCA Nexus,
  Global LCA Data Access, Plastics Europe, or other free-to-access sources,
  should remain supported as later benchmark adapters after the BAFU extract
  path is working.

Temporary files such as `~$BAFU Extract.xlsx` shall be ignored.

### 20.3 Task 1 End-to-End Steps

The system shall address Task 1 through the following complete workflow:

1. Intake and inventory
   - Discover files in the Task 1 corpus.
   - Preserve original file path, file name, file size, hash, and review run ID.
   - Ignore temporary or unsupported files without failing the whole run.

2. Document role classification
   - Classify each file as supplier PCF Excel, supplier PCF PDF, EPD, LCA
     report, SDS/supporting document, benchmark/reference data, guideline/rule
     document, oil-and-gas relevance source, or unrelated/unknown.
   - Prevent reference documents from being accidentally treated as supplier
     declarations.

3. Extraction
   - Extract structured Excel fields with cell-level evidence for known forms.
   - Extract PDF text/tables with page and snippet evidence for PDF examples.
   - Preserve an adapter path for text/email and PPT-derived supplier exchange
     formats, even if they are not first implemented.
   - Use LLM/agent assistance only as a schema-constrained helper for messy
     layouts, ambiguous labels, and semantic field mapping.

4. Canonical record population
   - Populate one canonical PCF review record per supplier product or chemical.
   - Support one document containing one product and the later case of one
     document containing multiple products.
   - Preserve original values, normalized values, extraction method, evidence,
     confidence, and uncertainty.

5. Unit and metadata normalization
   - Normalize PCF values to `kg CO2e / kg product` when declared unit,
     quantity, concentration, and product mass make this possible.
   - Preserve original values and mark normalization as uncertain when the
     declared unit, concentration, or product mass is ambiguous.
   - Normalize dates, standards, geography, product names, and database
     versions into stable internal representations.

6. Minimum requirement validation
   - Check PCF excluding biogenic carbon.
   - Check PCF including biogenic carbon where applicable.
   - Apply the fossil/non-biobased zero-biogenic exception.
   - Check system boundary, geography, reference year/period, accepted
     standards, product or sector rules, impact method, secondary database and
     version, attestation/certificate information, and oil-and-gas update status
     where relevant.
   - Return `pass`, `fail`, `missing`, `not_applicable`, or `uncertain` for
     each check.

7. Oil-and-gas relevance check
   - Match supplier product or raw material names against the oil-and-gas
     relevance source.
   - If relevant, check whether the supplier documentation proves the update
     was included.
   - Treat `ecoinvent 3.10` and `Sphera Managed Content 2024` as satisfying the
     update requirement unless contradictory evidence is found.

8. Benchmark/reference matching
   - Load the BAFU extract and preserve source identity.
   - Keep benchmark adapters source-aware so public sources such as openLCA
     Nexus, Global LCA Data Access, Plastics Europe, and future internal exports
     can be added without changing rule or decision logic.
   - Match by exact product name, aliases, normalized chemistry names, and
     fuzzy/semantic candidates.
   - Preserve benchmark source, matched dataset name, unit, region,
     concentration, production route, GWP100 value, confidence, and uncertainty.
   - Do not average regional reference values.

9. Plausibility calculation
   - Check dataset presence before final comparison.
   - Calculate percent deviation between supplier PCF and benchmark/reference
     value.
   - Flag deviations above 30 percent and unusually low or high values.
   - Route ambiguous matches, concentration/unit mismatches, and missing
     benchmark rows to human review.

10. Decision logic
    - Produce `accept`, `reject`, or `needs_human_review`.
    - Accept only when mandatory requirements pass or are not applicable and no
      significant unexplained benchmark issue remains.
    - Reject when mandatory data is clearly missing or a mandatory requirement
      clearly fails.
    - Use `needs_human_review` for extraction uncertainty, benchmark ambiguity,
      oil-and-gas uncertainty, or plausibility uncertainty.

11. Reporting and review output
    - Generate an Excel-compatible review workbook as the primary output.
    - Include summary, detailed rows, requirement checks, benchmark/match
      candidates, missing fields, follow-up questions, evidence index, and run
      log.
    - Clearly separate facts, inferred values, missing data, uncertain findings,
      automated rule results, and AI-assisted text.

12. Audit and traceability
    - Store typed JSON artifacts for extracted candidates, canonical records,
      requirement checks, match candidates, decisions, report rows, agent
      inputs/outputs, and run logs.
    - Preserve enough evidence to investigate a result months later.

### 20.4 Task 1 Depth Requirements for Spec Kit Artifacts

Every generated Spec Kit artifact for Task 1 shall retain this full workflow
depth. A feature spec must describe the user value and acceptance behavior for
all twelve steps. A plan must assign modules, schemas, artifacts, APIs, tests,
and risks to all twelve steps. A tasks file must create independently testable
work items for all twelve steps, with Excel-first implementation tasks before
PDF-expansion tasks.
