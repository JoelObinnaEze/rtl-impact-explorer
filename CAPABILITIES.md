# Capability Map: RTL Impact Explorer

| Module id | Responsibility | Depends on |
|---|---|---|
| `verilator-ingest` | Turn Verilator 5 JSON output into a stable, validated design model | — |
| `signal-graph` | Resolve signal nodes and directional driver/load relationships | `verilator-ingest` |
| `interactive-report` | Export a self-contained, searchable browser report | `signal-graph` |
| `cli-workflow` | Provide predictable commands for existing JSON and source-to-report flows | `verilator-ingest`, `signal-graph`, `interactive-report` |

Build order: `verilator-ingest` → `signal-graph` → `interactive-report` → `cli-workflow`.

