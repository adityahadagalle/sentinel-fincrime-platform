import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engines.graph_engine import (
    build_investigation_graph,
    add_node,
    add_edge,
    classify_topology_archetype
)

class TestForensicGraph(unittest.TestCase):
    def setUp(self):
        self.store = {
            "graphs": {},
            "transactions": {},
            "cases": {},
            "accounts": {}
        }

    def test_01_multi_hop_linear_chain_topology(self):
        case_id = "CASE-TEST-01"
        self.store["cases"][case_id] = {
            "case_id": case_id,
            "origin_account": "ACC-SRC-01",
            "chain": ["ACC-SRC-01", "ACC-MULE-01", "ACC-MULE-02", "ACC-EXIT-01"],
            "transactions": ["TX-101", "TX-102", "TX-103"]
        }
        self.store["transactions"]["TX-101"] = {
            "tx_id": "TX-101", "sender_account": "ACC-SRC-01", "receiver_account": "ACC-MULE-01",
            "amount": 100000.0, "hop_number": 1, "total_hops": 3, "case_id": case_id
        }
        self.store["transactions"]["TX-102"] = {
            "tx_id": "TX-102", "sender_account": "ACC-MULE-01", "receiver_account": "ACC-MULE-02",
            "amount": 95000.0, "hop_number": 2, "total_hops": 3, "case_id": case_id
        }
        self.store["transactions"]["TX-103"] = {
            "tx_id": "TX-103", "sender_account": "ACC-MULE-02", "receiver_account": "ACC-EXIT-01",
            "amount": 90000.0, "hop_number": 3, "total_hops": 3, "case_id": case_id
        }

        graph = build_investigation_graph(case_id, self.store, max_depth=5)
        self.assertGreaterEqual(len(graph["nodes"]), 4)
        self.assertEqual(len(graph["edges"]), 3)

        archetype = classify_topology_archetype(graph)
        self.assertIn(archetype, ["LINEAR_CHAIN", "STRUCTURING_PASS_THROUGH"])

    def test_02_fan_out_topology(self):
        case_id = "CASE-TEST-FANOUT"
        self.store["cases"][case_id] = {"case_id": case_id, "origin_account": "ACC-SRC-FAN", "transactions": ["T1", "T2", "T3"]}
        self.store["transactions"]["T1"] = {"tx_id": "T1", "sender_account": "ACC-SRC-FAN", "receiver_account": "MULE-A", "amount": 50000.0, "case_id": case_id}
        self.store["transactions"]["T2"] = {"tx_id": "T2", "sender_account": "ACC-SRC-FAN", "receiver_account": "MULE-B", "amount": 50000.0, "case_id": case_id}
        self.store["transactions"]["T3"] = {"tx_id": "T3", "sender_account": "ACC-SRC-FAN", "receiver_account": "MULE-C", "amount": 50000.0, "case_id": case_id}

        graph = build_investigation_graph(case_id, self.store, max_depth=5)
        self.assertEqual(len(graph["nodes"]), 4)
        self.assertEqual(len(graph["edges"]), 3)
        
        archetype = classify_topology_archetype(graph)
        self.assertEqual(archetype, "FAN_OUT")

    def test_03_fan_in_topology(self):
        case_id = "CASE-TEST-FANIN"
        self.store["cases"][case_id] = {"case_id": case_id, "origin_account": "COLLECTOR-01", "transactions": ["T1", "T2", "T3"]}
        self.store["transactions"]["T1"] = {"tx_id": "T1", "sender_account": "SRC-A", "receiver_account": "COLLECTOR-01", "amount": 30000.0, "case_id": case_id}
        self.store["transactions"]["T2"] = {"tx_id": "T2", "sender_account": "SRC-B", "receiver_account": "COLLECTOR-01", "amount": 30000.0, "case_id": case_id}
        self.store["transactions"]["T3"] = {"tx_id": "T3", "sender_account": "SRC-C", "receiver_account": "COLLECTOR-01", "amount": 30000.0, "case_id": case_id}

        graph = build_investigation_graph(case_id, self.store, max_depth=5)
        self.assertEqual(len(graph["nodes"]), 4)
        self.assertEqual(len(graph["edges"]), 3)
        
        archetype = classify_topology_archetype(graph)
        self.assertEqual(archetype, "FAN_IN")

if __name__ == "__main__":
    unittest.main()
