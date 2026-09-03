import unittest
from app.core.data_store import data_store
from app.engines.graph_engine import add_node, add_edge, get_graph

class TestGraphIntelligence(unittest.TestCase):
    def setUp(self):
        data_store["graphs"] = {}

    def test_01_node_and_edge_intelligence(self):
        case_id = "CASE-GRAPH-01"
        
        # Add source node
        add_node(case_id, {
            "account_id": "ACC-SRC-01",
            "status": "active",
            "current_balance_sim": 500000.0,
            "risk_score": 25.0
        }, data_store)

        # Add mule node
        add_node(case_id, {
            "account_id": "ACC-MULE-01",
            "status": "flagged",
            "current_balance_sim": 120000.0,
            "risk_score": 85.0
        }, data_store)

        # Add edge
        add_edge(case_id, "ACC-SRC-01", "ACC-MULE-01", "TX-MULE-01", 250000.0, data_store, {
            "hop_number": 1,
            "total_hops": 3,
            "chain_id": "CHAIN-001",
            "pattern_type": "MULE_CHAIN"
        })

        graph = get_graph(case_id, data_store)
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(len(graph["edges"]), 1)

        src_node = next(n for n in graph["nodes"] if n["id"] == "ACC-SRC-01")
        mule_node = next(n for n in graph["nodes"] if n["id"] == "ACC-MULE-01")

        self.assertEqual(src_node["outbound_count"], 1)
        self.assertEqual(mule_node["inbound_count"], 1)
        self.assertEqual(mule_node["account_type"], "MULE")

        edge = graph["edges"][0]
        self.assertEqual(edge["hop_number"], 1)
        self.assertEqual(edge["total_hops"], 3)
        self.assertEqual(edge["pattern_type"], "MULE_CHAIN")

if __name__ == "__main__":
    unittest.main()
