import urllib.request
import json

timeframes = ['24h', '7d', '30d', '12m']
for tf in timeframes:
    url = f"http://127.0.0.1:8000/analytics/overview?timeframe={tf}"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    actions = data.get('action_outcomes', [])
    auto = data.get('automation_intelligence', {})
    total = sum(a['count'] for a in actions)
    print(f"=== TIMEFRAME: {tf} ===")
    print(f"Total actions: {total}, Automation Intel Total: {auto.get('total_actions_recorded')}")
    pct_sum = 0.0
    for a in actions:
        pct_sum += a.get('percentage', 0.0)
        print(f"  {a['action']:20} count={a['count']} ({a['percentage']}%) status={a.get('status')}")
    print(f"Sum of percentages: {pct_sum:.1f}%\n")
