import urllib.request
import json

res = urllib.request.urlopen('http://127.0.0.1:8000/cases')
cases = json.loads(res.read())

cases_with_chain = [c for c in cases if c.get('chain_id')]
print(f"Cases with chain_id: {len(cases_with_chain)}")

for c in cases_with_chain[:5]:
    cid = c['case_id']
    chain_id = c.get('chain_id')
    txs = c.get('transactions', [])
    print(f"\nCase {cid}, chain_id={chain_id}, tx count={len(txs)}")
    for t in txs:
        tid = t.get('tx_id') if isinstance(t, dict) else str(t)
        try:
            tg_res = urllib.request.urlopen(f'http://127.0.0.1:8000/transactions/{tid}/graph')
            tg = json.loads(tg_res.read())
            print(f"  Tx {tid}: {len(tg.get('nodes', []))} nodes, {len(tg.get('edges', []))} edges, topology={tg.get('topology_type')}")
        except Exception as e:
            print(f"  Tx {tid} error: {e}")
