import unittest
from app.engines.graph_engine import add_node, add_edge, get_graph

class TestMultiHopChains(unittest.TestCase):
    def setUp(self):
        self.store = {"graphs": {}}

    def test_multi_hop_metadata_and_stats(self):
        case_id = "CASE-MH-TEST-001"
        
        # Add 5 nodes (Mule chain path)
        add_node(case_id, {"account_id": "ACC-USR-1023", "account_type": "SOURCE"}, self.store)
        add_node(case_id, {"account_id": "ACC-MULE-4821", "account_type": "MULE"}, self.store)
        add_node(case_id, {"account_id": "ACC-INT-7732", "account_type": "INTERMEDIARY"}, self.store)
        add_node(case_id, {"account_id": "ACC-MULE-9182", "account_type": "MULE"}, self.store)
        add_node(case_id, {"account_id": "ACC-MERCH-4412", "account_type": "DESTINATION"}, self.store)

        # Add 4 multi-hop edges
        add_edge(case_id, "ACC-USR-1023", "ACC-MULE-4821", "TX-1", 98000.0, self.store, extra={
            "hop_number": 1, "total_hops": 4, "pattern_type": "MULE_CHAIN", "chain_id": "CHAIN-MH-01"
        })
        add_edge(case_id, "ACC-MULE-4821", "ACC-INT-7732", "TX-2", 95000.0, self.store, extra={
            "hop_number": 2, "total_hops": 4, "pattern_type": "MULE_CHAIN", "chain_id": "CHAIN-MH-01"
        })
        add_edge(case_id, "ACC-INT-7732", "ACC-MULE-9182", "TX-3", 92000.0, self.store, extra={
            "hop_number": 3, "total_hops": 4, "pattern_type": "MULE_CHAIN", "chain_id": "CHAIN-MH-01"
        })
        add_edge(case_id, "ACC-MULE-9182", "ACC-MERCH-4412", "TX-4", 90000.0, self.store, extra={
            "hop_number": 4, "total_hops": 4, "pattern_type": "MULE_CHAIN", "chain_id": "CHAIN-MH-01"
        })

        graph = get_graph(case_id, self.store)
        self.assertEqual(len(graph["nodes"]), 5)
        self.assertEqual(len(graph["edges"]), 4)

        # Check edge metadata
        first_edge = graph["edges"][0]
        self.assertEqual(first_edge["hop_number"], 1)
        self.assertEqual(first_edge["total_hops"], 4)
        self.assertEqual(first_edge["pattern_type"], "MULE_CHAIN")
        self.assertEqual(first_edge["chain_id"], "CHAIN-MH-01")

        # Check node flow statistics recalculation
        mule1_node = next(n for n in graph["nodes"] if n["account_id"] == "ACC-MULE-4821")
        self.assertEqual(mule1_node["inbound_count"], 1)
        self.assertEqual(mule1_node["outbound_count"], 1)
        self.assertEqual(mule1_node["total_inbound"], 98000.0)
        self.assertEqual(mule1_node["total_outbound"], 95000.0)

    def test_single_hop_backward_compatibility(self):
        case_id = "CASE-LEGACY-001"
        add_node(case_id, {"account_id": "ACC-LEGACY-A"}, self.store)
        add_node(case_id, {"account_id": "ACC-LEGACY-B"}, self.store)
        add_edge(case_id, "ACC-LEGACY-A", "ACC-LEGACY-B", "TX-LEGACY-1", 500.0, self.store)

        graph = get_graph(case_id, self.store)
        edge = graph["edges"][0]
        self.assertEqual(edge["hop_number"], 1)
        self.assertEqual(edge["total_hops"], 1)
        self.assertEqual(edge["pattern_type"], "STANDARD")

if __name__ == "__main__":
    unittest.main()
