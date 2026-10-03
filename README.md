# RTL Impact Explorer

RTL Impact Explorer turns an elaborated SystemVerilog design into a searchable, interactive map of signal drivers and loads. It is built for the question that usually starts a long debug session:

> If this signal changes, what logic can it affect—and what can affect it?

The output is a local, fetch-free report that opens directly in a browser. Select a signal, move through its cross-hierarchy connections, switch between driver and load cones, and inspect source locations without starting a simulator.

## Why this project exists

[Dara-O's VeriTrace](https://github.com/Dara-O/veritrace) demonstrated a useful idea: use Verilator's elaborated representation to make RTL connectivity explorable. RTL Impact Explorer is an independent implementation and credits that MIT-licensed project as its inspiration.

The important modernization is the ingestion format. VeriTrace used Verilator XML; Verilator 5.052 removed the deprecated XML flags. This project targets the supported [`--json-only`](https://verilator.org/guide/latest/exe_verilator.html) output instead.

## Current capabilities

- Verilator 5 JSON ingestion with source-file metadata.
- Elaborated module hierarchy and per-instance signals.
- Directional connections across assignments, sequential processes, and module ports.
- Bounded multi-hop fan-in and fan-out traversal.
- Search and module filtering.
- Responsive, keyboard-accessible browser report.
- Native Verilator execution with automatic Docker fallback.
- No Python runtime dependencies.

## Quick start

Requirements:

- Python 3.11 or newer.
- Either a native Verilator executable or Docker with the official Verilator image.

Install the development package:

```powershell
py -m pip install -e .
```

Analyze the included two-module design:

```powershell
rtl-impact analyze examples/counter_top.sv `
  --top counter_top `
  --output report `
  --engine auto
```

Then open `report/index.html`. The report uses local JavaScript assets and an embedded data assignment, so it also works directly from `file://` without a web server.

If Verilator JSON already exists:

```powershell
rtl-impact analyze-json obj_dir/Vcounter_top.tree.json `
  --meta obj_dir/Vcounter_top.tree.meta.json `
  --output report
```

Run `rtl-impact --help`, `rtl-impact analyze --help`, or `rtl-impact analyze-json --help` for the complete command contract.

## How the graph is built

The parser creates a stable project-owned model rather than exposing Verilator's evolving AST directly:

```text
SystemVerilog
    │
    ▼
Verilator --json-only
    │
    ▼
typed instances + signals + source locations
    │
    ├── process reads ──▶ process writes
    └── parent signal ◀──▶ child module port
    │
    ▼
versioned report payload → interactive dependency cone
```

Process edges are conservative dependencies, not bit-accurate proofs. A signal read by an `always_ff` or combinational process is connected to every signal written by that process. This intentionally captures control dependencies such as enables and resets, but it can over-approximate complex blocks.

## Development

Run the complete test suite:

```powershell
$env:PYTHONPATH = "src"
py -m unittest discover -s tests -v
```

Check the browser JavaScript:

```powershell
node --check src/rtl_impact_explorer/web/app.js
node --check src/rtl_impact_explorer/web/graph-view.js
```

Regenerate the real Verilator fixture with Docker:

```powershell
docker run --rm -v "${PWD}:/work" verilator/verilator:latest `
  --json-only --no-json-edit-nums `
  --json-only-output /work/tests/fixtures/counter_top.tree.json `
  --json-only-meta-output /work/tests/fixtures/counter_top.tree.meta.json `
  --top-module counter_top /work/examples/counter_top.sv
```

## A 60-second recruiter demo

1. Search for `active_o`.
2. Switch the graph to **Drivers** and depth **3**.
3. Follow `count_o → pulse_o → terminal_count → active_o` across the child-module boundary.
4. Select `enable_i` or `run_i` to reverse the question and show downstream impact.
5. Point out the JSON compatibility layer, deterministic tests, local artifact, and clean dependency-free frontend.

## Deliberate limits

- The tool requires Verilator to elaborate the design; it is not a standalone SystemVerilog parser.
- The graph is signal-level and process-level, not bit-select precise.
- Functions, tasks, interfaces, arrays, and exotic data types need broader fixture coverage.
- Git change-impact comparison, clock/reset-domain analysis, and large-design graph virtualization are roadmap items.

See [SPEC.md](SPEC.md) for the complete contract and [tasks/plan.md](tasks/plan.md) for the implementation slices.

## Attribution

- Inspired by [Dara-O/veritrace](https://github.com/Dara-O/veritrace), Copyright © 2023 Isaac Ogunmola, distributed under the MIT License.
- Verilator is a separate open-source project maintained under its own licenses. See the [Verilator documentation](https://verilator.org/guide/latest/).

No source code from VeriTrace is included in this implementation.
