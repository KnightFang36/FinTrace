"""Render an already-bounded network with inline PyVis resources and escaped labels."""
from html import escape
import json
import math
import networkx as nx
import streamlit as st
from pyvis.network import Network
from fintrace.contracts import content_id


def network_positions(view):
    """Bounded presentation layout: separate connected groups and avoid collisions."""
    graph = nx.Graph()
    graph.add_nodes_from(sorted(node['id'] for node in view['nodes']))
    graph.add_edges_from(sorted((edge['from'], edge['to']) for edge in view['edges']))
    if len(graph) > 200 or len(view['edges']) > 500:
        raise ValueError('Network layout exceeds the display budget')
    boxes = []
    # Layout each component independently: disconnected accounts cannot squeeze
    # dense fan-in/out groups into tiny areas of a global spring layout.
    components = sorted(nx.connected_components(graph), key=lambda group: (-len(group), tuple(sorted(group))))
    for members in components:
        component = graph.subgraph(sorted(members))
        raw = nx.spring_layout(component, seed=42, iterations=80, weight=None,
                               scale=140 * math.sqrt(len(members)))
        keys = sorted(members)
        points = {key: [float(raw[key][0]), float(raw[key][1])] for key in keys}
        # Fixed iteration budget, then a final scale ensures measurable spacing.
        # These are display distances, never inferred transfers or time order.
        for _ in range(45):
            changed = False
            for index, left in enumerate(keys):
                for right in keys[index+1:]:
                    dx = points[right][0] - points[left][0]
                    dy = points[right][1] - points[left][1]
                    distance = math.hypot(dx, dy)
                    target = 280 if component.has_edge(left, right) else 180
                    if distance >= target:
                        continue
                    if distance < 1e-9:
                        dx, dy, distance = 1.0, 0.0, 1.0
                    shift = (target - distance) / (2 * distance)
                    points[left][0] -= dx * shift
                    points[left][1] -= dy * shift
                    points[right][0] += dx * shift
                    points[right][1] += dy * shift
                    changed = True
            if not changed:
                break
        factor = max((
            (280 if component.has_edge(left, right) else 180) /
            max(math.dist(points[left], points[right]), 1e-9)
            for index, left in enumerate(keys) for right in keys[index+1:]
        ), default=1)
        factor = max(1, factor)
        for point in points.values():
            point[0] *= factor
            point[1] *= factor
        minimum_x = min(point[0] for point in points.values())
        minimum_y = min(point[1] for point in points.values())
        width = max(point[0] for point in points.values()) - minimum_x + 200
        height = max(point[1] for point in points.values()) - minimum_y + 200
        boxes.append((points, minimum_x, minimum_y, width, height))
    if not boxes:
        return {}
    row_limit = max(max(box[3] for box in boxes), math.sqrt(sum(box[3]*box[4] for box in boxes)*1.6))
    positions, x, y, row_height = {}, 0, 0, 0
    for points, minimum_x, minimum_y, width, height in boxes:
        if x and x + width > row_limit:
            x, y, row_height = 0, y + row_height, 0
        for key, point in points.items():
            positions[key] = (point[0] - minimum_x + x + 100, point[1] - minimum_y + y + 100)
        x += width
        row_height = max(row_height, height)
    center_x = (min(point[0] for point in positions.values()) + max(point[0] for point in positions.values())) / 2
    center_y = (min(point[1] for point in positions.values()) + max(point[1] for point in positions.values())) / 2
    return {key: (point[0]-center_x, point[1]-center_y) for key, point in positions.items()}


def network_html(view):
    network = Network(height="720px", width="100%", directed=True, bgcolor="#0b1420", font_color="#e8f0fa", cdn_resources="in_line")
    positions = network_positions(view)
    for node in view["nodes"]:
        account = node["account"]
        label = escape(f"{account['bank_id']}:{account['account_id']}")
        title = label
        if 'rank' in node:
            title += f" | Rank {node['rank']} | Review priority {node['score']}/100 | Active alerts {node['active_alerts']}"
        if node.get('missing_from_window'):
            title += " | No transfers in the selected graph window"
        network.add_node(node["id"], label=label, title=title, color="#ffbf69" if node["seed"] else "#38d9c5",
                         size=22 if node["seed"] else 14, shape="diamond" if node.get('missing_from_window') else "dot",
                         x=float(positions[node['id']][0]), y=float(positions[node['id']][1]), physics=False,
                         review_rank=node.get('rank'), review_subject=node['seed'], font={'size': 18})
    for edge in view["edges"]:
        tx = edge["transaction"]
        title = escape(f"{tx['transaction_id']} | {tx['occurred_at']} | Paid {tx['amount_paid']} {tx['payment_currency']} | Received {tx['amount_received']} {tx['receiving_currency']}")
        network.add_edge(edge["from"], edge["to"], id=content_id(edge["id"]), title=title,
                         color="#ffbf69" if edge["highlighted"] else "#829cb8", width=5 if edge["highlighted"] else 3,
                         arrows={"to": {"enabled": True, "scaleFactor": 1.6}}, smooth={"enabled": True, "type": "continuous"})
    network.set_options(json.dumps({"layout": {"randomSeed": 42, "improvedLayout": False}, "physics": {"enabled": False},
                                   "interaction": {"hover": True, "navigationButtons": True}, "edges": {"arrows": {"to": {"enabled": True}}}}))
    html = network.generate_html()
    # PyVis's base template includes optional Bootstrap CDN references even with inline vis.js.
    import re
    html = re.sub(r'<link[^>]*href="https://[^>]+>', '', html)
    html = re.sub(r'<script[^>]*src="https://[^>]+>\s*</script>', '', html)
    html = html.replace("</head>", """<style>
      html, body, .card { margin: 0; background: #0b1420; color: #e8f0fa; }
      * { box-sizing: border-box; }
      #ft-graph-shell { background: #0b1420; color: #e8f0fa; width: 100%; }
      #ft-graph-toolbar { display: flex; align-items: center; gap: 8px; height: 48px; padding: 6px 10px; }
      #ft-graph-toolbar button { background: #17283b; color: #e8f0fa; border: 1px solid #62809f;
                                border-radius: 5px; padding: 7px 12px; cursor: pointer; font: 14px sans-serif; }
      #ft-graph-toolbar button:hover { background: #223e56; }
      #ft-graph-toolbar button:focus-visible { outline: 2px solid #38d9c5; outline-offset: 2px; }
      #ft-graph-status { color: #ffbf69; font: 13px sans-serif; margin: 0; }
      #mynetwork { border: 1px solid #2a3e55 !important; border-radius: 6px; height: 720px !important; }
      #ft-graph-shell:fullscreen { width: 100vw; height: 100vh; }
      #ft-graph-shell:fullscreen #mynetwork { height: calc(100vh - 48px) !important; border-radius: 0; }
      div.vis-tooltip { background: #17283b; color: #e8f0fa; border: 1px solid #62809f;
                        padding: 10px; font: 13px/1.5 sans-serif; max-width: 500px; overflow-wrap: anywhere; }
    </style></head>""")
    html = html.replace('<div id="mynetwork" class="card-body"></div>', '''<section id="ft-graph-shell" aria-label="Transaction network">
      <div id="ft-graph-toolbar">
        <button type="button" id="ft-fullscreen" aria-pressed="false">Full screen</button>
        <button type="button" id="ft-readable">Readable view</button>
        <button type="button" id="ft-fit">Fit graph</button>
        <span id="ft-graph-status" role="status" aria-live="polite"></span>
      </div>
      <div id="mynetwork" class="card-body"></div>
    </section>''')
    html = html.replace('</body>', '''<script>
      const shell = document.getElementById('ft-graph-shell');
      const fullscreenButton = document.getElementById('ft-fullscreen');
      const status = document.getElementById('ft-graph-status');
      function fitGraph() { network.redraw(); network.fit({animation: false}); }
      function readableGraph() {
        const subjects = network.body.data.nodes.get().filter(node => node.review_subject);
        subjects.sort((a,b) => (a.review_rank ?? 999) - (b.review_rank ?? 999) || a.id.localeCompare(b.id));
        const focus = subjects[0] || network.body.data.nodes.get()[0];
        network.redraw();
        if (focus) network.moveTo({position: network.getPositions([focus.id])[focus.id], scale: 0.7, animation: false});
      }
      fullscreenButton.addEventListener('click', async () => {
        status.textContent = '';
        try {
          if (document.fullscreenElement === shell) await document.exitFullscreen();
          else await shell.requestFullscreen();
          fullscreenButton.focus();
        } catch (error) {
          status.textContent = 'Full screen is unavailable in this browser.';
        }
      });
      document.addEventListener('fullscreenchange', () => {
        const expanded = document.fullscreenElement === shell;
        fullscreenButton.textContent = expanded ? 'Exit full screen' : 'Full screen';
        fullscreenButton.setAttribute('aria-pressed', String(expanded));
        requestAnimationFrame(() => requestAnimationFrame(() => network.redraw()));
      });
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && document.fullscreenElement === shell) {
          document.exitFullscreen().catch(() => {
            status.textContent = 'Use Exit full screen to close the expanded graph.';
          });
        }
      });
      document.getElementById('ft-fit').addEventListener('click', fitGraph);
      document.getElementById('ft-readable').addEventListener('click', readableGraph);
      requestAnimationFrame(readableGraph);
    </script></body>''')
    return html


def render_network(view):
    missing_count = len(view.get('missing_seeds', []))
    extra = f" · {missing_count} ranked accounts outside the graph window" if missing_count else ""
    st.caption(f"{len(view['nodes']) - missing_count} / {view['source_nodes']:,} graph-window accounts{extra} · {len(view['edges'])} / {view['source_edges']:,} transfers · orange edges = selected evidence")
    if view["partial"]:
        st.info("Bounded view of the selected graph window. Accounts and edges outside this view remain in the underlying evidence.")
    if not view["evidence_complete"]:
        st.warning("Some selected evidence is outside this graph or exceeds the display budget. Use the evidence transaction list for the complete references.")
    st.iframe(network_html(view), height=780, alt="Interactive directed transaction network with full-screen control")
    st.caption("Longer edges · fixed layout · pan to explore the readable view · Fit graph shows the whole selection · Full screen to enlarge · Esc to exit. Structural links alone do not establish a temporal money flow.")
