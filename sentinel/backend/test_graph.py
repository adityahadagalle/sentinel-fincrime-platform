from app.core.data_store import data_store
from app.engines.graph_engine import build_investigation_graph

cases = list(data_store.get('cases', {}).keys())
txs = list(data_store.get('transactions', {}).keys())
print(f"Total cases in store: {len(cases)}, total txs in store: {len(txs)}")

for cid in cases[:5]:
    g = build_investigation_graph(cid, data_store)
    print(f"Case {cid}: {len(g.get('nodes', []))} nodes, {len(g.get('edges', []))} edges, topology: {g.get('topology_type')}")
    for e in g.get('edges', [])[:3]:
        print(f"   edge: {e.get('from')} -> {e.get('to')} (₹{e.get('amount')})")

print("\n--- Testing Transactions ---")
for tid in txs[:6]:
    tx = data_store['transactions'][tid]
    g = build_investigation_graph(tx.get('case_id', ''), data_store, focus_tx_id=tid)
    print(f"TX {tid} ({tx.get('sender_account')} -> {tx.get('receiver_account')}): {len(g.get('nodes', []))} nodes, {len(g.get('edges', []))} edges, topology: {g.get('topology_type')}")
    for e in g.get('edges', []):
        print(f"   edge: {e.get('from')} -> {e.get('to')} (₹{e.get('amount')})")
