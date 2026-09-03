import unittest
from app.engines.graph_engine import add_node, add_edge, build_investigation_graph, DEFAULT_GRAPH_HOPS, MAX_GRAPH_HOPS
from app.services.orchestrator import run_pipeline

class TestMultiHopGraphTraversal(unittest.TestCase):
    def setUp(self):
        self.store = {"graphs": {}, "cases": {}, "transactions": {}, "accounts": {}}

    def test_01_normal_transaction_returns_one_edge(self):
        tx = {
            "tx_id": "TX-NORM-01",
            "sender_account": "ACC-USR-01",
            "receiver_account": "ACC-MERCH-01",
            "amount": 1200.0,
            "risk_score": 80
        }
        res = run_pipeline(tx, self.store)
        case_id = res["case"]["case_id"]
        graph = build_investigation_graph(case_id, self.store)
        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(len(graph["nodes"]), 2)


    def test_02_three_hop_scenario_returns_three_edges(self):
        chain_id = "CHAIN-3HOP-TEST"
        case_id = "CASE-3HOP-TEST"
        nodes = ["ACC-USR-10", "ACC-INT-11", "ACC-MULE-12", "ACC-MERCH-13"]
        for i in range(len(nodes) - 1):
            tx = {
                "tx_id": f"TX-3H-0{i+1}",
                "case_id": case_id,
                "sender_account": nodes[i],
                "receiver_account": nodes[i+1],
                "amount": 40000.0 - (i * 1000),
                "risk_score": 75,
                "chain_id": chain_id,
                "hop_number": i + 1,
                "total_hops": 3,
                "pattern_type": "3_HOP_TRANSFER"
            }
            run_pipeline(tx, self.store)

        graph = build_investigation_graph(case_id, self.store)
        self.assertEqual(len(graph["edges"]), 3)
        self.assertEqual(len(graph["nodes"]), 4)

    def test_03_five_hop_mule_chain_returns_five_edges_and_six_nodes(self):
        chain_id = "CHAIN-5HOP-TEST"
        case_id = "CASE-5HOP-TEST"
        nodes = ["ACC-SRC-01", "ACC-MULE-01", "ACC-INT-01", "ACC-MULE-02", "ACC-INT-02", "ACC-DEST-01"]
        root_tx_id = "TX-5H-01"
        for i in range(len(nodes) - 1):
            tx = {
                "tx_id": f"TX-5H-0{i+1}",
                "case_id": case_id,
                "sender_account": nodes[i],
                "receiver_account": nodes[i+1],
                "amount": 90000.0 - (i * 2000),
                "risk_score": 80 + i,
                "chain_id": chain_id,
                "hop_number": i + 1,
                "total_hops": 5,
                "pattern_type": "MULE_CHAIN",
                "parent_transaction_id": f"TX-5H-0{i}" if i > 0 else None,
                "root_transaction_id": root_tx_id
            }
            run_pipeline(tx, self.store)

        graph = build_investigation_graph(case_id, self.store)
        self.assertEqual(len(graph["edges"]), 5)
        self.assertEqual(len(graph["nodes"]), 6)

        # Check edge metadata & order
        for idx, edge in enumerate(sorted(graph["edges"], key=lambda e: e["hop_number"])):
            self.assertEqual(edge["hop_number"], idx + 1)
            self.assertEqual(edge["total_hops"], 5)
            self.assertEqual(edge["root_transaction_id"], root_tx_id)

    def test_04_funnel_returns_multiple_inbound_edges(self):
        case_id = "CASE-FUNNEL-TEST"
        senders = ["ACC-S1", "ACC-S2", "ACC-S3", "ACC-S4"]
        funnel = "ACC-FUNNEL-01"
        dest = "ACC-DEST-01"

        for i, s_acc in enumerate(senders):
            tx = {
                "tx_id": f"TX-FN-IN-0{i+1}",
                "case_id": case_id,
                "sender_account": s_acc,
                "receiver_account": funnel,
                "amount": 10000.0,
                "risk_score": 70,
                "pattern_type": "FUNNEL_ACCOUNT"
            }
            run_pipeline(tx, self.store)

        run_pipeline({
            "tx_id": "TX-FN-OUT-01",
            "case_id": case_id,
            "sender_account": funnel,
            "receiver_account": dest,
            "amount": 40000.0,
            "risk_score": 85,
            "pattern_type": "FUNNEL_ACCOUNT"
        }, self.store)

        graph = build_investigation_graph(case_id, self.store)
        self.assertEqual(len(graph["edges"]), 5)
        self.assertEqual(len(graph["nodes"]), 6)

        funnel_node = next(n for n in graph["nodes"] if n["id"] == funnel)
        self.assertEqual(funnel_node["inbound_count"], 4)
        self.assertEqual(funnel_node["outbound_count"], 1)

    def test_05_fanout_returns_multiple_outbound_edges(self):
        case_id = "CASE-FANOUT-TEST"
        source = "ACC-SRC-FAN"
        receivers = ["ACC-REC-1", "ACC-REC-2", "ACC-REC-3", "ACC-REC-4"]

        for i, r_acc in enumerate(receivers):
            tx = {
                "tx_id": f"TX-FO-0{i+1}",
                "case_id": case_id,
                "sender_account": source,
                "receiver_account": r_acc,
                "amount": 15000.0,
                "risk_score": 80,
                "pattern_type": "FAN_OUT"
            }
            run_pipeline(tx, self.store)

        graph = build_investigation_graph(case_id, self.store)
        self.assertEqual(len(graph["edges"]), 4)
        self.assertEqual(len(graph["nodes"]), 5)

        src_node = next(n for n in graph["nodes"] if n["id"] == source)
        self.assertEqual(src_node["outbound_count"], 4)

    def test_06_circular_scenario_contains_cycle(self):
        case_id = "CASE-CIRCULAR-TEST"
        nodes = ["ACC-A-10", "ACC-B-10", "ACC-C-10", "ACC-D-10", "ACC-A-10"]

        for i in range(len(nodes) - 1):
            tx = {
                "tx_id": f"TX-CIRC-0{i+1}",
                "case_id": case_id,
                "sender_account": nodes[i],
                "receiver_account": nodes[i+1],
                "amount": 50000.0,
                "risk_score": 90,
                "pattern_type": "CIRCULAR_FLOW"
            }
            run_pipeline(tx, self.store)

        graph = build_investigation_graph(case_id, self.store)
        self.assertEqual(len(graph["edges"]), 4)
        self.assertEqual(len(graph["nodes"]), 4)

    def test_07_account_relationship_traversal_without_chain_id(self):
        # Legacy / unlabeled multi-hop transaction chain
        case_id = "CASE-LEGACY-BFS"
        run_pipeline({"tx_id": "TX-L1", "case_id": case_id, "sender_account": "ACC-L1", "receiver_account": "ACC-L2", "amount": 1000.0, "risk_score": 60}, self.store)
        run_pipeline({"tx_id": "TX-L2", "sender_account": "ACC-L2", "receiver_account": "ACC-L3", "amount": 1000.0, "risk_score": 60}, self.store)
        run_pipeline({"tx_id": "TX-L3", "sender_account": "ACC-L3", "receiver_account": "ACC-L4", "amount": 1000.0, "risk_score": 60}, self.store)

        graph = build_investigation_graph(case_id, self.store, max_depth=5)
        self.assertEqual(len(graph["edges"]), 3)
        self.assertEqual(len(graph["nodes"]), 4)

    def test_08_bounded_traversal_respects_max_graph_hops(self):
        self.assertEqual(DEFAULT_GRAPH_HOPS, 5)
        self.assertEqual(MAX_GRAPH_HOPS, 8)
        case_id = "CASE-BOUNDED-TEST"

        # Create 10 hops (11 nodes)
        nodes = [f"ACC-NODE-{i:02d}" for i in range(11)]
        for i in range(len(nodes) - 1):
            tx = {
                "tx_id": f"TX-BND-{i:02d}",
                "case_id": case_id if i == 0 else None,
                "sender_account": nodes[i],
                "receiver_account": nodes[i+1],
                "amount": 5000.0,
                "risk_score": 65
            }
            run_pipeline(tx, self.store)

        graph = build_investigation_graph(case_id, self.store, max_depth=12)
        # Should be bounded by MAX_GRAPH_HOPS (8)
        self.assertLessEqual(len(graph["edges"]), MAX_GRAPH_HOPS)

if __name__ == "__main__":
    unittest.main()
