(function () {
  "use strict";

  const svgNs = "http://www.w3.org/2000/svg";

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS(svgNs, name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
  }

  function buildAdjacency(edges) {
    const drivers = new Map();
    const loads = new Map();
    edges.forEach((edge) => {
      if (!loads.has(edge.source)) loads.set(edge.source, []);
      if (!drivers.has(edge.target)) drivers.set(edge.target, []);
      loads.get(edge.source).push(edge.target);
      drivers.get(edge.target).push(edge.source);
    });
    return { drivers, loads };
  }

  function walk(start, adjacency, depth, sign) {
    const levels = new Map([[start, 0]]);
    let frontier = [start];
    for (let step = 1; step <= depth; step += 1) {
      const next = new Set();
      frontier.forEach((node) => {
        (adjacency.get(node) || []).forEach((neighbor) => {
          if (!levels.has(neighbor)) {
            levels.set(neighbor, step * sign);
            next.add(neighbor);
          }
        });
      });
      frontier = [...next].sort();
      if (!frontier.length) break;
    }
    return levels;
  }

  function graphLevels(selectedId, edges, direction, depth) {
    const { drivers, loads } = buildAdjacency(edges);
    const levels = new Map([[selectedId, 0]]);
    if (direction !== "loads") {
      walk(selectedId, drivers, depth, -1).forEach((level, id) => levels.set(id, level));
    }
    if (direction !== "drivers") {
      walk(selectedId, loads, depth, 1).forEach((level, id) => {
        if (!levels.has(id) || Math.abs(level) < Math.abs(levels.get(id))) levels.set(id, level);
      });
    }
    return levels;
  }

  function shorten(value, limit) {
    return value.length <= limit ? value : `…${value.slice(-(limit - 1))}`;
  }

  function renderGraph({ svg, signals, edges, selectedId, direction, depth, onSelect }) {
    svg.replaceChildren();
    const signalMap = new Map(signals.map((signal) => [signal.id, signal]));
    if (!signalMap.has(selectedId)) return { nodeCount: 0, edgeCount: 0 };

    const levels = graphLevels(selectedId, edges, direction, depth);
    const includedEdges = edges.filter((edge) => levels.has(edge.source) && levels.has(edge.target));
    const width = Math.max(svg.clientWidth || 760, 560);
    const height = Math.max(svg.clientHeight || 520, 420);
    const xPadding = 112;
    const yPadding = 68;
    const layerValues = [...new Set(levels.values())].sort((a, b) => a - b);
    const layerIndex = new Map(layerValues.map((value, index) => [value, index]));
    const byLayer = new Map(layerValues.map((value) => [value, []]));
    levels.forEach((level, id) => byLayer.get(level).push(id));
    byLayer.forEach((items) => items.sort());

    const positions = new Map();
    byLayer.forEach((ids, level) => {
      const x = layerValues.length === 1
        ? width / 2
        : xPadding + (layerIndex.get(level) * (width - xPadding * 2)) / (layerValues.length - 1);
      ids.forEach((id, index) => {
        const y = yPadding + ((index + 1) * (height - yPadding * 2)) / (ids.length + 1);
        positions.set(id, { x, y });
      });
    });

    const defs = svgElement("defs");
    const marker = svgElement("marker", {
      id: "arrowhead",
      markerWidth: 8,
      markerHeight: 8,
      refX: 7,
      refY: 4,
      orient: "auto",
      markerUnits: "strokeWidth",
    });
    marker.append(svgElement("path", { d: "M 0 0 L 8 4 L 0 8 z" }));
    defs.append(marker);
    svg.append(defs);

    const edgeLayer = svgElement("g", { class: "edge-layer" });
    includedEdges.forEach((edge) => {
      const start = positions.get(edge.source);
      const end = positions.get(edge.target);
      if (!start || !end) return;
      const bend = Math.max(36, Math.abs(end.x - start.x) * 0.45);
      const path = svgElement("path", {
        class: `graph-edge ${edge.kind}`,
        d: `M ${start.x + 82} ${start.y} C ${start.x + bend} ${start.y}, ${end.x - bend} ${end.y}, ${end.x - 82} ${end.y}`,
        "marker-end": "url(#arrowhead)",
      });
      const title = svgElement("title");
      title.textContent = `${signalMap.get(edge.source).name} → ${signalMap.get(edge.target).name} (${edge.kind})`;
      path.append(title);
      edgeLayer.append(path);
    });
    svg.append(edgeLayer);

    const nodeLayer = svgElement("g", { class: "node-layer" });
    positions.forEach((position, id) => {
      const signal = signalMap.get(id);
      const group = svgElement("g", {
        class: `graph-node ${id === selectedId ? "selected" : ""}`,
        transform: `translate(${position.x - 82} ${position.y - 29})`,
        tabindex: 0,
        role: "button",
        "aria-label": `Select ${signal.path}`,
      });
      group.append(svgElement("rect", { width: 164, height: 58, rx: 4 }));
      const name = svgElement("text", { x: 12, y: 24, class: "node-name" });
      name.textContent = shorten(signal.name, 20);
      const module = svgElement("text", { x: 12, y: 43, class: "node-module" });
      module.textContent = shorten(signal.modulePath, 23);
      group.append(name, module);
      group.addEventListener("click", () => onSelect(id));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(id);
        }
      });
      nodeLayer.append(group);
    });
    svg.append(nodeLayer);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    return { nodeCount: levels.size, edgeCount: includedEdges.length };
  }

  window.RtlGraphView = { renderGraph };
}());

