import urllib.request
import json

res = urllib.request.urlopen('http://127.0.0.1:8000/cases')
cases = json.loads(res.read())

# Print summary of case types
print(f"Total cases: {len(cases)}")
for c in cases[:10]:
    cid = c['case_id']
    tx_list = c.get('transactions', [])
    print(f"Case {cid}: {len(tx_list)} transactions")
