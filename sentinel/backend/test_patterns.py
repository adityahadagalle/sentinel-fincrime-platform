import urllib.request
import json

res = urllib.request.urlopen('http://127.0.0.1:8000/cases')
cases = json.loads(res.read())

print("Testing transaction graphs for different case patterns:")
tested_patterns = set()

for c in cases:
    cid = c.get('case_id')
    nodes = c.get('nodes', [])
    edges = c.get('edges', [])
    ttype = c.get('topology_type')
    
    # Let's inspect edges of this case
    if len(edges) >= 2 and cid:
        for e in edges:
            tid = e.get('tx_id')
            if tid:
                try:
                    tres = urllib.request.urlopen(f'http://127.0.0.1:8000/transactions/{tid}/graph')
                    tg = json.loads(tres.read())
                    t_nodes = len(tg.get('nodes', []))
                    t_edges = len(tg.get('edges', []))
                    edge_str = " | ".join([f"{ed.get('from')}->{ed.get('to')}" for ed in tg.get('edges', [])])
                    print(f"\nCase {cid} ({len(nodes)} nodes, {len(edges)} edges) -> TX {tid}:")
                    print(f"   Result: {t_nodes} nodes, {t_edges} edges, topology: {tg.get('topology_type')}")
                    print(f"   Edges: {edge_str}")
                    break
                except Exception as ex:
                    print(f"Error on {tid}: {ex}")
        if len(tested_patterns) > 5:
            break
