# Tasks

- [x] Capture a real Verilator 5.052 JSON fixture and add failing ingestion tests.
  - Acceptance: modules, signals, locations, and assignments are represented in a typed model.
  - Verify: `py -m unittest tests.test_verilator_json -v`
  - Files: `tests/fixtures/*`, `tests/test_verilator_json.py`, `src/rtl_impact_explorer/model.py`, `src/rtl_impact_explorer/verilator_json.py`

- [ ] Build directional signal graph queries test-first.
  - Acceptance: direct and bounded transitive drivers/loads are deterministic and deduplicated.
  - Verify: `py -m unittest tests.test_signal_graph -v`
  - Files: `tests/test_signal_graph.py`, `src/rtl_impact_explorer/signal_graph.py`

- [ ] Generate a self-contained interactive report.
  - Acceptance: output includes the schema payload and all local assets required from `file://`.
  - Verify: `py -m unittest tests.test_report -v`, then browser inspection.
  - Files: `tests/test_report.py`, `src/rtl_impact_explorer/report.py`, `src/rtl_impact_explorer/web/*`

- [ ] Add CLI workflows, example, and user documentation.
  - Acceptance: both public commands follow documented exit/error behavior and the sample command creates a report.
  - Verify: `py -m unittest discover -s tests -v`
  - Files: `tests/test_cli.py`, `src/rtl_impact_explorer/cli.py`, `src/rtl_impact_explorer/__main__.py`, `examples/*`, `README.md`, `pyproject.toml`
