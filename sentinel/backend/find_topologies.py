import urllib.request
import json

res = urllib.request.urlopen('http://127.0.0.1:8000/cases')
cases = json.loads(res.read())

# Let's inspect the cases in data_store directly or via endpoints
# Let's see what transactions exist in cases:
multihop_cases = []
branching_cases = []

for c in cases:
    cid = c.get('case_id')
    nodes = c.get('nodes', [])
    edges = c.get('edges', [])
    if len(edges) > 1:
        # Check connectivity of edges
        sources = set(e.get('from') or e.get('source') for e in edges)
        targets = set(e.get('to') or e.get('target') for e in edges)
        
        # Check if there's an intermediate node (both target of one and source of another)
        intermediates = sources.intersection(targets)
        if intermediates:
            multihop_cases.append((cid, len(nodes), len(edges), list(intermediates)))
            
        # Check branching (one source has multiple targets)
        src_counts = {}
        for e in edges:
            s = e.get('from') or e.get('source')
            src_counts[s] = src_counts.get(s, 0) + 1
        splits = [s for s, cnt in src_counts.items() if cnt > 1]
        if splits:
            branching_cases.append((cid, len(nodes), len(edges), splits))

print(f"Cases with multi-hop chains: {len(multihop_cases)}")
for item in multihop_cases[:5]:
    print(f"  Case {item[0]}: {item[1]} nodes, {item[2]} edges, intermediate nodes: {item[3]}")

print(f"\nCases with branching/splits: {len(branching_cases)}")
for item in branching_cases[:5]:
    print(f"  Case {item[0]}: {item[1]} nodes, {item[2]} edges, split source nodes: {item[3]}")
