import urllib.request
import json

tiers = [
    ("SAFE (Direct Retail)", "CASE-SAFE-01", "TX-SAFE-1001", 2, 1),
    ("NORMAL (2-Hop Relay)", "CASE-NORM-02", "TX-NORM-2001", 3, 2),
    ("BRANCHING (Fan-Out)", "CASE-BRANCH-03", "TX-BRANCH-3001", 6, 5),
    ("FRAUD (7-Node Layered)", "CASE-FRAUD-600", "TX-FRAUD-6001", 7, 6),
]

print("=== VERIFYING TOPOLOGY TIERS (CASES & TRANSACTIONS) ===")
all_passed = True
for name, cid, tid, exp_nodes, exp_edges in tiers:
    # 1. Test by Case Graph
    c_res = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8000/cases/{cid}/graph").read())
    c_nodes = len(c_res.get("nodes", []))
    c_edges = len(c_res.get("edges", []))
    c_arch = c_res.get("topology_type")
    
    # 2. Test by Transaction Graph
    t_res = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8000/transactions/{tid}/graph").read())
    t_nodes = len(t_res.get("nodes", []))
    t_edges = len(t_res.get("edges", []))
    t_arch = t_res.get("topology_type")

    print(f"\n[+] {name}:")
    print(f"    Case {cid} Graph: {c_nodes} nodes, {c_edges} edges, archetype: {c_arch}")
    print(f"    Tx   {tid} Graph: {t_nodes} nodes, {t_edges} edges, archetype: {t_arch}")

    if c_nodes != exp_nodes or c_edges != exp_edges:
        print(f"    [FAIL] Expected Case ({exp_nodes}, {exp_edges}) but got ({c_nodes}, {c_edges})")
        all_passed = False
    elif t_nodes != exp_nodes or t_edges != exp_edges:
        print(f"    [FAIL] Expected Tx ({exp_nodes}, {exp_edges}) but got ({t_nodes}, {t_edges})")
        all_passed = False
    else:
        print(f"    [PASS] Strict complexity parity achieved!")

print("\n" + "="*50)
if all_passed:
    print("ALL TOPOLOGY TIERS VERIFIED SUCCESSFULLY!")
else:
    print("SOME TOPOLOGIES FAILED VALIDATION.")

print("\n=== VERIFYING INTERMEDIATE HOPS IN FRAUD CHAIN ===")
for tid in ["TX-FRAUD-6001", "TX-FRAUD-6002", "TX-FRAUD-6003", "TX-FRAUD-6004", "TX-FRAUD-6005", "TX-FRAUD-6006"]:
    t_res = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8000/transactions/{tid}/graph").read())
    print(f"Selecting {tid} -> Graph: {len(t_res.get('nodes', []))} nodes, {len(t_res.get('edges', []))} edges, archetype: {t_res.get('topology_type')}")

