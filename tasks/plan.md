# RTL Impact Explorer MVP Plan

## Slice 1 — Contract and ingestion

Define the versioned report schema and parse a real Verilator 5 JSON fixture into typed modules, signals, and assignments.

Checkpoint: focused parser tests pass against malformed and valid fixtures.

## Slice 2 — Signal graph

Convert assignment references into directional signal edges and expose deterministic fan-in/fan-out queries.

Checkpoint: graph tests cover direct, multi-hop, and disconnected signals.

## Slice 3 — Self-contained report

Export data and static assets, then implement the searchable hierarchy, dependency canvas, and signal details panel.

Checkpoint: integration tests validate the output artifact; a real browser verifies visuals, keyboard flow, and a clean console.

## Slice 4 — CLI and documentation

Connect existing-JSON and source-to-report commands, add the example workflow, and document setup, attribution, limitations, and demo talking points.

Checkpoint: CLI integration tests and the full suite pass; the documented sample command creates the reviewed report.

## Risks and mitigations

- Verilator's JSON format is documented as evolving: isolate it behind one parser and retain small versioned fixtures.
- AST assignments can contain complex expressions: recursively collect variable references and label edge confidence; do not imply bit-accurate dataflow.
- Large graphs can overwhelm SVG: show a bounded dependency cone, never the entire design at once.
- `file://` blocks fetch requests: embed the validated data in a JavaScript assignment rather than loading JSON at runtime.

