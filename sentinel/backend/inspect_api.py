import urllib.request
import json

res = urllib.request.urlopen('http://127.0.0.1:8000/cases')
cases = json.loads(res.read())

for c in cases[:6]:
    cid = c.get('case_id')
    txs = c.get('transactions', [])
    for t in txs[:2]:
        tid = t if isinstance(t, str) else t.get('tx_id')
        try:
            tres = urllib.request.urlopen(f'http://127.0.0.1:8000/transactions/{tid}/graph')
            tg = json.loads(tres.read())
            print(f"TX {tid} (in {cid}): {len(tg.get('nodes', []))} nodes, {len(tg.get('edges', []))} edges, topology: {tg.get('topology_type')}")
            for e in tg.get('edges', []):
                print(f"   edge: {e.get('from')} -> {e.get('to')} (amt: {e.get('amount')}) id={e.get('id')}")
        except Exception as ex:
            print(f"TX {tid} error: {ex}")
