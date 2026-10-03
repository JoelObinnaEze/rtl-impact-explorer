# Spec: RTL Impact Explorer MVP

## Objective

Build a local-first static-analysis tool for RTL engineers and hardware recruiters. The tool consumes the supported JSON AST produced by Verilator 5.052+, extracts a navigable signal-dependency graph, and exports a polished self-contained browser report.

The primary portfolio story is: select a signal, inspect its drivers and loads across the elaborated hierarchy, and jump to source context without opening a simulator.

### Acceptance scenarios

1. Given a valid Verilator `.tree.json` file, `analyze-json` produces an `index.html` that works without a web server.
2. The report shows design statistics, module hierarchy, searchable signals, and directional drivers/loads.
3. Selecting a signal updates the dependency view and an accessible details panel.
4. Invalid JSON or an unsupported AST shape exits non-zero with a concise error.
5. The core parser and graph traversal run entirely on the Python standard library.

## Tech Stack

- Python 3.11+ standard library for the CLI, parser, graph model, and exporter.
- Verilator 5.052+ `--json-only` output as the external elaboration contract.
- HTML, CSS, and modern browser JavaScript with no runtime CDN or package dependency.
- `unittest` for deterministic unit and integration tests.

## Commands

```powershell
# Run all tests
py -m unittest discover -s tests -v

# Analyze existing Verilator JSON
py -m rtl_impact_explorer analyze-json obj_dir/Vtop.tree.json --output report

# Run Verilator and generate a report
py -m rtl_impact_explorer analyze examples/counter_top.sv --top counter_top --output report

# Preview the generated artifact
py -m http.server 8000 --directory report
```

## Public Interfaces

### CLI

```text
rtl-impact analyze-json INPUT --output DIR [--title TITLE]
rtl-impact analyze SOURCE... --top MODULE --output DIR [--verilator PATH]
```

- Successful commands return exit code `0`.
- User/input/tool errors return exit code `1` and a single `error: ...` message on stderr.
- `--help` and argparse usage errors retain argparse's standard behavior.
- Existing output assets are replaced file-by-file; unrelated files in the output directory are preserved.

### Report data schema

The generated JavaScript payload exposes one additive, versioned object:

```javascript
window.RTL_IMPACT_DATA = {
  schemaVersion: 1,
  design: { name: "counter_top", source: "Vcounter_top.tree.json" },
  summary: { modules: 2, signals: 9, connections: 7 },
  modules: [],
  signals: [],
  edges: []
};
```

Required identifiers are stable within one analyzed artifact. Future fields may be added; existing schema-1 fields will not change meaning.

## Project Structure

```text
src/rtl_impact_explorer/  Python package and CLI
src/rtl_impact_explorer/web/  Static report assets
tests/                   Unit and integration tests
tests/fixtures/          Small Verilator JSON fixtures
examples/                Demonstration SystemVerilog
tasks/                   Implementation plan and checklist
```

## Code Style

Use typed dataclasses and small boundary functions. External input is validated once, then internal code relies on the model.

```python
@dataclass(frozen=True, slots=True)
class Signal:
    id: str
    name: str
    path: str
    direction: str
    width: int
```

- `snake_case` for Python functions and fields; `PascalCase` for types.
- Explicit return types for public functions.
- Browser code uses `camelCase` and semantic DOM elements.
- No dependency or abstraction is added without a current MVP use case.

## Testing Strategy

- Unit tests: input validation, AST traversal, width/location decoding, graph traversal.
- Integration tests: fixture JSON to complete report directory.
- Browser verification: load the generated report, inspect console and accessibility structure, search for a signal, and trace both directions.
- Every behavioral change starts with a failing focused test and ends with the full suite.

## Design Contract

- Screen job: explain one selected signal's place in an elaborated RTL design.
- Primary action: search for and select a signal.
- Layout: dense three-column engineering workspace on desktop; stacked panels below 900 px.
- Visual language: dark graphite workbench, cyan signal paths, amber driver emphasis, restrained borders, monospace for RTL identifiers.
- Required states: populated design, no search matches, signal with no drivers, signal with no loads, parse error in the CLI.
- Reject: generic marketing hero, card-grid dashboard, decorative gradients, inaccessible click-only rows, and CDN dependencies.

## Boundaries

- Always: validate external JSON, escape embedded report data, preserve keyboard navigation, run tests before commits.
- Ask first: new runtime dependencies, a hosted backend, telemetry, or changing the report schema incompatibly.
- Never: execute input RTL in the browser, load remote scripts, expose local source contents beyond file/line metadata, or claim complete SystemVerilog semantic coverage.

## Success Criteria

- The sample design produces a report containing at least two modules and a multi-hop signal relationship.
- Search, module filtering, signal selection, and direction switching work with mouse and keyboard.
- The generated report opens from `file://` without fetch/CORS failures.
- The browser console contains no errors or warnings during the demo flow.
- All tests pass on Python 3.11+ with no third-party package installed.
- README documents attribution to Dara-O's MIT-licensed VeriTrace as inspiration and explains the JSON modernization.

## Not in MVP

- Git revision comparison or change-impact scoring.
- Waveform viewing, simulation, synthesis, timing, or formal analysis.
- A full SystemVerilog parser independent of Verilator.
- IDE extensions, hosted accounts, collaboration, or cloud storage.
- Legacy Verilator XML ingestion.

## Open Questions

- Which real-world open-source core should become the public benchmark after the sample design?
- Should the first post-MVP release prioritize Git change-impact mode or clock/reset-domain analysis?

