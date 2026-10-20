"""Render an already-bounded network with inline PyVis resources and escaped labels."""
from html import escape
import json
import networkx as nx
import streamlit as st
from pyvis.network import Network
from fintrace.contracts import content_id


def network_html(view):
    network = Network(height="560px", width="100%", directed=True, bgcolor="#0b1420", font_color="#e8f0fa", cdn_resources="in_line")
    # Compute bounded, reproducible positions once; never run browser physics.
    layout_graph = nx.Graph()
    layout_graph.add_nodes_from(sorted(node['id'] for node in view['nodes']))
    layout_graph.add_edges_from(sorted((edge['from'], edge['to']) for edge in view['edges']))
    positions = nx.spring_layout(layout_graph, seed=42, iterations=60, scale=800)
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
                         x=float(positions[node['id']][0]), y=float(positions[node['id']][1]), physics=False)
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
      #mynetwork { border: 1px solid #2a3e55 !important; border-radius: 6px; height: 560px !important; }
      #ft-graph-shell:fullscreen { width: 100vw; height: 100vh; }
      #ft-graph-shell:fullscreen #mynetwork { height: calc(100vh - 48px) !important; border-radius: 0; }
      div.vis-tooltip { background: #17283b; color: #e8f0fa; border: 1px solid #62809f;
                        padding: 10px; font: 13px/1.5 sans-serif; max-width: 500px; overflow-wrap: anywhere; }
    </style></head>""")
    html = html.replace('<div id="mynetwork" class="card-body"></div>', '''<section id="ft-graph-shell" aria-label="Transaction network">
      <div id="ft-graph-toolbar">
        <button type="button" id="ft-fullscreen" aria-pressed="false">Full screen</button>
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
        requestAnimationFrame(() => requestAnimationFrame(fitGraph));
      });
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && document.fullscreenElement === shell) {
          document.exitFullscreen().catch(() => {
            status.textContent = 'Use Exit full screen to close the expanded graph.';
          });
        }
      });
      document.getElementById('ft-fit').addEventListener('click', fitGraph);
      requestAnimationFrame(fitGraph);
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
    st.iframe(network_html(view), height=620, alt="Interactive directed transaction network with full-screen control")
    st.caption("Fixed layout · drag to explore · scroll to zoom · Full screen to enlarge · Esc to exit. Structural links alone do not establish a temporal money flow.")
