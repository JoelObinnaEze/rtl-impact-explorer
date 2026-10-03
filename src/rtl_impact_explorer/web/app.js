(function () {
  "use strict";

  const data = window.RTL_IMPACT_DATA;
  const graphView = window.RtlGraphView;
  const signalMap = new Map((data?.signals || []).map((signal) => [signal.id, signal]));
  const state = {
    selectedId: data?.signals.find((signal) => signal.direction === "output")?.id || data?.signals[0]?.id,
    modulePath: null,
    query: "",
    direction: "both",
    depth: 2,
  };

  const elements = Object.fromEntries([
    "designTitle", "moduleCount", "signalCount", "edgeCount", "signalSearch", "clearSearch",
    "moduleList", "showAllModules", "signalList", "visibleSignalCount", "emptySignals",
    "resetFilters", "graphCanvas", "traceDepth", "graphStatus", "detailsHeading", "selectedPath",
    "signalBadges", "sourceDetails", "driverList", "driverCount", "loadList", "loadCount",
    "artifactSource",
  ].map((id) => [id, document.getElementById(id)]));

  function button(label, className, onClick) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = className;
    item.textContent = label;
    item.addEventListener("click", onClick);
    return item;
  }

  function directConnections(signalId, direction) {
    const ids = data.edges
      .filter((edge) => direction === "drivers" ? edge.target === signalId : edge.source === signalId)
      .map((edge) => direction === "drivers" ? edge.source : edge.target);
    return [...new Set(ids)].sort();
  }

  function selectSignal(signalId) {
    if (!signalMap.has(signalId)) return;
    state.selectedId = signalId;
    renderSignals();
    renderSelection();
  }

  function renderModules() {
    elements.moduleList.replaceChildren();
    data.modules.forEach((module) => {
      const row = button(module.path, "module-row", () => {
        state.modulePath = state.modulePath === module.path ? null : module.path;
        renderModules();
        renderSignals();
      });
      row.setAttribute("aria-pressed", String(state.modulePath === module.path));
      row.style.setProperty("--depth", String(module.path.split(".").length - 1));
      const count = document.createElement("span");
      count.textContent = String(module.signalIds.length);
      count.className = "module-count";
      row.append(count);
      elements.moduleList.append(row);
    });
  }

  function visibleSignals() {
    const query = state.query.trim().toLowerCase();
    return data.signals.filter((signal) => {
      const inModule = !state.modulePath || signal.modulePath === state.modulePath;
      const matches = !query || signal.path.toLowerCase().includes(query);
      return inModule && matches;
    });
  }

  function renderSignals() {
    const signals = visibleSignals();
    elements.signalList.replaceChildren();
    signals.forEach((signal) => {
      const item = document.createElement("li");
      const row = button(signal.name, "signal-row", () => selectSignal(signal.id));
      row.setAttribute("aria-current", signal.id === state.selectedId ? "true" : "false");
      const type = document.createElement("span");
      type.className = `direction-mark ${signal.direction}`;
      type.textContent = signal.direction === "internal" ? "int" : signal.direction.slice(0, 3);
      const width = document.createElement("span");
      width.className = "signal-width";
      width.textContent = signal.width > 1 ? `${signal.width}b` : "1b";
      row.prepend(type);
      row.append(width);
      item.append(row);
      elements.signalList.append(item);
    });
    elements.visibleSignalCount.textContent = String(signals.length);
    elements.emptySignals.hidden = signals.length !== 0;
  }

  function renderConnectionList(target, countTarget, ids, emptyText) {
    target.replaceChildren();
    countTarget.textContent = String(ids.length);
    if (!ids.length) {
      const item = document.createElement("li");
      item.className = "connection-empty";
      item.textContent = emptyText;
      target.append(item);
      return;
    }
    ids.forEach((id) => {
      const item = document.createElement("li");
      item.append(button(signalMap.get(id)?.path || id, "connection-button", () => selectSignal(id)));
      target.append(item);
    });
  }

  function renderSelection() {
    const signal = signalMap.get(state.selectedId);
    if (!signal) return;
    elements.detailsHeading.textContent = signal.name;
    elements.selectedPath.textContent = signal.path;
    elements.signalBadges.replaceChildren();
    [signal.direction, `${signal.width} bit${signal.width === 1 ? "" : "s"}`, signal.dtype].forEach((label) => {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = label;
      elements.signalBadges.append(badge);
    });
    elements.sourceDetails.replaceChildren();
    const sourceRows = [
      ["Module", signal.modulePath],
      ["File", signal.source.file || "Unknown"],
      ["Location", signal.source.line ? `line ${signal.source.line}:${signal.source.column || 1}` : "Unknown"],
    ];
    sourceRows.forEach(([term, description]) => {
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = term;
      dd.textContent = description;
      elements.sourceDetails.append(dt, dd);
    });
    const drivers = directConnections(signal.id, "drivers");
    const loads = directConnections(signal.id, "loads");
    renderConnectionList(elements.driverList, elements.driverCount, drivers, "No known drivers");
    renderConnectionList(elements.loadList, elements.loadCount, loads, "No known loads");
    const stats = graphView.renderGraph({
      svg: elements.graphCanvas,
      signals: data.signals,
      edges: data.edges,
      selectedId: signal.id,
      direction: state.direction,
      depth: state.depth,
      onSelect: selectSignal,
    });
    elements.graphStatus.textContent = `${signal.path}: showing ${stats.nodeCount} signals and ${stats.edgeCount} connections.`;
  }

  function resetFilters() {
    state.modulePath = null;
    state.query = "";
    elements.signalSearch.value = "";
    renderModules();
    renderSignals();
  }

  function initialise() {
    if (!data || data.schemaVersion !== 1 || !graphView) {
      document.body.textContent = "This report is missing compatible RTL Impact Explorer data.";
      return;
    }
    elements.designTitle.textContent = data.design.title;
    elements.moduleCount.textContent = data.summary.modules;
    elements.signalCount.textContent = data.summary.signals;
    elements.edgeCount.textContent = data.summary.connections;
    elements.artifactSource.textContent = data.design.source;
    renderModules();
    renderSignals();
    renderSelection();

    elements.signalSearch.addEventListener("input", (event) => {
      state.query = event.target.value;
      renderSignals();
    });
    elements.clearSearch.addEventListener("click", () => {
      state.query = "";
      elements.signalSearch.value = "";
      elements.signalSearch.focus();
      renderSignals();
    });
    elements.showAllModules.addEventListener("click", resetFilters);
    elements.resetFilters.addEventListener("click", resetFilters);
    elements.traceDepth.addEventListener("change", (event) => {
      state.depth = Number(event.target.value);
      renderSelection();
    });
    document.querySelectorAll("[data-direction]").forEach((control) => {
      control.addEventListener("click", () => {
        state.direction = control.dataset.direction;
        document.querySelectorAll("[data-direction]").forEach((item) => {
          item.setAttribute("aria-pressed", String(item === control));
        });
        renderSelection();
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && document.activeElement !== elements.signalSearch) {
        event.preventDefault();
        elements.signalSearch.focus();
      }
      if (event.key === "Escape" && document.activeElement === elements.signalSearch) resetFilters();
    });
    let resizeFrame;
    window.addEventListener("resize", () => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(renderSelection);
    });
  }

  initialise();
}());

