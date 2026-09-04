import urllib.request
import json

res = urllib.request.urlopen('http://127.0.0.1:8000/cases')
cases = json.loads(res.read())
print(f"Total cases: {len(cases)}")

# Find cases with multiple transactions or different topologies
multi_tx_cases = [c for c in cases if len(c.get('transactions', [])) > 1]
print(f"Multi-tx cases: {len(multi_tx_cases)}")

sample_cases = multi_tx_cases[:3] if multi_tx_cases else cases[:5]

for specific_tx in ['TX-1A544A-01', 'TX-1A544A-02', 'TX-1A544A-06', 'TX-CFF83D-01']:
    try:
        tg_res = urllib.request.urlopen(f'http://127.0.0.1:8000/transactions/{specific_tx}/graph')
        tg = json.loads(tg_res.read())
        print(f"\nSpecific Tx {specific_tx} graph:")
        print(f"  Nodes ({len(tg.get('nodes', []))}):", [n.get('id') for n in tg.get('nodes', [])])
        print(f"  Edges ({len(tg.get('edges', []))}):", [(e.get('from'), '->', e.get('to'), e.get('tx_id')) for e in tg.get('edges', [])])
        print(f"  Topology: {tg.get('topology_type')}")
    except Exception as ex:
        print(f"\nSpecific Tx {specific_tx} error: {ex}")
