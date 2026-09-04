import hashlib
from typing import Optional, List, Dict, Any

def get_graph(case_id: str, store: dict) -> dict:
    if "graphs" not in store:
        store["graphs"] = {}
    if case_id not in store["graphs"]:
        return {"nodes": [], "edges": []}
    return store["graphs"][case_id]


def add_node(case_id: str, account: dict, store: dict):
    if "graphs" not in store:
        store["graphs"] = {}
    if case_id not in store["graphs"]:
        store["graphs"][case_id] = {"nodes": [], "edges": []}
        
    graph = store["graphs"][case_id]
    account_id = account.get("account_id") or account.get("accountId") or account.get("id")
    if not account_id:
        return
        
    acc_type = account.get("account_type")
    node_type = account.get("node_type")
    if not acc_type or not node_type:
        sid = str(account_id).upper()
        if "MULE" in sid:
            acc_type = acc_type or "MULE"
            node_type = node_type or "mule"
        elif "INT" in sid or "FUNNEL" in sid or "SHARED" in sid or "COLL" in sid:
            acc_type = acc_type or "INTERMEDIARY"
            node_type = node_type or "collector"
        elif "MERCH" in sid or "DRAIN" in sid or "EXIT" in sid or "CASH" in sid or "ATM" in sid:
            acc_type = acc_type or "DESTINATION"
            node_type = node_type or "cashout"
        elif "UPI" in sid:
            acc_type = acc_type or "INTERMEDIARY"
            node_type = node_type or "UPI"
        elif "CRYPTO" in sid:
            acc_type = acc_type or "DESTINATION"
            node_type = node_type or "crypto"
        else:
            acc_type = acc_type or "SOURCE"
            node_type = node_type or "victim"

    for n in graph["nodes"]:
        if n.get("account_id") == account_id or n.get("accountId") == account_id:
            if account.get("status"):
                n["status"] = account["status"]
            if "current_balance_sim" in account:
                n["balance"] = float(account["current_balance_sim"])
            if acc_type:
                n["account_type"] = acc_type
            if node_type:
                n["node_type"] = node_type
            return

    graph["nodes"].append({
        "account_id": str(account_id),
        "accountId": str(account_id),
        "id": str(account_id),
        "status": account.get("status", "active"),
        "balance": float(account.get("current_balance_sim", 0.0)),
        "account_type": acc_type,
        "node_type": node_type,
        "layer": int(account.get("layer", 0)),
        "inbound_count": int(account.get("inbound_count", 0)),
        "outbound_count": int(account.get("outbound_count", 0)),
        "total_inbound": float(account.get("total_inbound", 0.0)),
        "total_outbound": float(account.get("total_outbound", 0.0)),
        "risk_score": float(account.get("risk_score", 0.0))
    })


def add_edge(case_id: str, from_acc: str, to_acc: str, tx_id: str, amount: float, store: dict, extra: dict = None):
    if "graphs" not in store:
        store["graphs"] = {}
    if case_id not in store["graphs"]:
        store["graphs"][case_id] = {"nodes": [], "edges": []}
        
    graph = store["graphs"][case_id]
    extra = extra or {}
    
    for e in graph["edges"]:
        if e.get("tx_id") == tx_id:
            e.update({
                "from": from_acc,
                "to": to_acc,
                "source": from_acc,
                "target": to_acc,
                "amount": float(amount),
                "hop_number": extra.get("hop_number", e.get("hop_number", 1)),
                "total_hops": extra.get("total_hops", e.get("total_hops", 1)),
                "chain_id": extra.get("chain_id", e.get("chain_id")),
                "pattern_type": extra.get("pattern_type", e.get("pattern_type")),
                "suspicious": extra.get("suspicious", e.get("suspicious", True)),
                "channel": extra.get("channel", e.get("channel", "UPI")),
                "parent_transaction_id": extra.get("parent_transaction_id", e.get("parent_transaction_id")),
                "root_transaction_id": extra.get("root_transaction_id", e.get("root_transaction_id")),
                "timestamp": extra.get("timestamp", e.get("timestamp", ""))
            })
            _recalculate_node_stats(graph)
            return
        
    edge_obj = {
        "id": str(tx_id),
        "from": str(from_acc),
        "to": str(to_acc),
        "source": str(from_acc),
        "target": str(to_acc),
        "tx_id": str(tx_id),
        "amount": float(amount),
        "hop_number": int(extra.get("hop_number", 1)),
        "total_hops": int(extra.get("total_hops", 1)),
        "chain_id": extra.get("chain_id") or f"CHAIN-{tx_id[:8]}",
        "pattern_type": extra.get("pattern_type") or "STANDARD",
        "suspicious": bool(extra.get("suspicious", True)),
        "channel": extra.get("channel", "UPI"),
        "parent_transaction_id": extra.get("parent_transaction_id"),
        "root_transaction_id": extra.get("root_transaction_id") or tx_id,
        "timestamp": extra.get("timestamp", "")
    }
    graph["edges"].append(edge_obj)
    _recalculate_node_stats(graph)


def _recalculate_node_stats(graph: dict):
    """Calculates node flow metrics, degree counts, and topological layer depths."""
    stats = {}
    for node in graph.get("nodes", []):
        nid = node.get("account_id") or node.get("id")
        if nid:
            stats[nid] = {
                "inbound_count": 0,
                "outbound_count": 0,
                "total_inbound": 0.0,
                "total_outbound": 0.0
            }

    for edge in graph.get("edges", []):
        src = edge.get("from") or edge.get("source")
        tgt = edge.get("to") or edge.get("target")
        amt = float(edge.get("amount", 0.0))
        if src in stats:
            stats[src]["outbound_count"] += 1
            stats[src]["total_outbound"] += amt
        if tgt in stats:
            stats[tgt]["inbound_count"] += 1
            stats[tgt]["total_inbound"] += amt

    for node in graph.get("nodes", []):
        nid = node.get("account_id") or node.get("id")
        if nid in stats:
            node.update(stats[nid])

    # Assign topological layers via Breadth-First Search from source nodes (inbound_count == 0)
    node_map = {n.get("account_id") or n.get("id"): n for n in graph.get("nodes", [])}
    adj = {}
    in_degree = {nid: 0 for nid in node_map}
    for edge in graph.get("edges", []):
        src = edge.get("from") or edge.get("source")
        tgt = edge.get("to") or edge.get("target")
        if src not in adj:
            adj[src] = []
        adj[src].append(tgt)
        if tgt in in_degree:
            in_degree[tgt] += 1

    sources = [nid for nid, deg in in_degree.items() if deg == 0]
    if not sources and node_map:
        sources = [list(node_map.keys())[0]]

    visited = {}
    queue = [(s, 0) for s in sources]
    while queue:
        curr, depth = queue.pop(0)
        if curr in visited and visited[curr] <= depth:
            continue
        visited[curr] = depth
        for nxt in adj.get(curr, []):
            queue.append((nxt, depth + 1))

    max_layer = 0
    for nid, node in node_map.items():
        layer_val = visited.get(nid, 0)
        node["layer"] = layer_val
        max_layer = max(max_layer, layer_val)
        
        sid = str(nid).upper()
        if layer_val == 0 and not node.get("node_type"):
            node["node_type"] = "victim"
        elif "MULE" in sid:
            node["node_type"] = node.get("node_type") or "mule"
        elif "COLL" in sid or "INT" in sid or "HUB" in sid:
            node["node_type"] = node.get("node_type") or "collector"
        elif "UPI" in sid:
            node["node_type"] = node.get("node_type") or "UPI"
        elif "CRYPTO" in sid:
            node["node_type"] = node.get("node_type") or "crypto"
        elif "MERCH" in sid:
            node["node_type"] = node.get("node_type") or "merchant"
        elif layer_val >= 3 or "CASH" in sid or "ATM" in sid or "DRAIN" in sid:
            node["node_type"] = node.get("node_type") or "cashout"
        elif not node.get("node_type"):
            node["node_type"] = "individual"

        # Calculate or inherit node risk scores from connected transactions and archetype
        curr_risk = float(node.get("risk_score", 0.0))
        if curr_risk <= 0.0:
            connected_risks = [
                float(e.get("risk_score", 0.0))
                for e in graph.get("edges", [])
                if (e.get("from") == nid or e.get("to") == nid or e.get("source") == nid or e.get("target") == nid)
                and float(e.get("risk_score", 0.0)) > 0.0
            ]
            max_edge_risk = max(connected_risks) if connected_risks else 0.0
            ntype = str(node.get("node_type", "")).lower()
            nstatus = str(node.get("status", "")).upper()

            if ntype == "victim" or layer_val == 0:
                node["risk_score"] = 15.0
            elif nstatus in ("FLAGGED", "FROZEN"):
                node["risk_score"] = max(max_edge_risk, 85.0) if max_edge_risk > 0 else 88.0
            elif ntype == "mule":
                node["risk_score"] = max_edge_risk if max_edge_risk > 0 else 85.0
            elif ntype in ("cashout", "crypto"):
                node["risk_score"] = max(max_edge_risk, 88.0) if max_edge_risk > 0 else 92.0
            elif ntype == "merchant":
                node["risk_score"] = max_edge_risk if max_edge_risk > 0 else 65.0
            elif ntype == "collector":
                node["risk_score"] = max_edge_risk if max_edge_risk > 0 else 80.0
            else:
                node["risk_score"] = max_edge_risk if max_edge_risk > 0 else 20.0

    graph["max_hops"] = max(max_layer, 1)


DEFAULT_GRAPH_HOPS = 5
MAX_GRAPH_HOPS = 8


def classify_topology_archetype(graph: dict) -> str:
    """Classifies graph structure into topology archetypes based on genuine topology."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not edges or not nodes:
        return "NONE"

    out_degrees = {}
    in_degrees = {}
    for e in edges:
        src = e.get("from") or e.get("source")
        tgt = e.get("to") or e.get("target")
        out_degrees[src] = out_degrees.get(src, 0) + 1
        in_degrees[tgt] = in_degrees.get(tgt, 0) + 1

    # Check Circular Loop
    for e in edges:
        src = e.get("from") or e.get("source")
        tgt = e.get("to") or e.get("target")
        if src == tgt:
            return "CIRCULAR_LOOP"

    max_out = max(out_degrees.values()) if out_degrees else 0
    max_in = max(in_degrees.values()) if in_degrees else 0

    if max_out >= 2 and max_out > max_in:
        return "FAN_OUT"
    if max_in >= 2 and max_in > max_out:
        return "FAN_IN"
    if len(edges) == 1 and len(nodes) == 2:
        return "DIRECT_TRANSFER"
    if len(nodes) >= 4 and len(edges) >= 3:
        return "STRUCTURING_PASS_THROUGH"

    return "LINEAR_CHAIN"





def build_investigation_graph(case_id: str, store: dict, max_depth: int = DEFAULT_GRAPH_HOPS, focus_tx_id: Optional[str] = None) -> dict:
    """
    Dynamically builds the authentic transaction network graph for a focused transaction or case.
    Strictly data-driven:
    - 2-node direct transfer -> 2 nodes, 1 edge
    - Multi-hop chain -> all real intermediary mules/accounts in sequence
    - Branching / split -> real fan-out or fan-in topology
    Zero synthetic padding, zero fake disconnected nodes.
    """
    if "graphs" not in store:
        store["graphs"] = {}

    all_txs = list(store.get("transactions", {}).values())
    case_obj = store.get("cases", {}).get(case_id, {})
    account_store = store.get("accounts", {})

    # If focused on a specific transaction, build an authentic transaction-anchored graph
    if focus_tx_id:
        f_tx = store.get("transactions", {}).get(focus_tx_id)
        if not f_tx:
            for t in all_txs:
                if t.get("tx_id") == focus_tx_id:
                    f_tx = t
                    break

        if not f_tx:
            return {
                "nodes": [],
                "edges": [],
                "primary_tx_id": focus_tx_id,
                "case_id": case_id,
                "topology_type": "NONE"
            }

        f_snd = f_tx.get("sender_account")
        f_rcv = f_tx.get("receiver_account")
        f_cid = f_tx.get("chain_id")
        f_rid = f_tx.get("root_transaction_id") or focus_tx_id
        f_case = f_tx.get("case_id") or case_id

        nodes_by_id = {}
        edges_by_tx = {}

        def _add_account_node(acc_id: str, default_type: str = "MULE"):
            if not acc_id or acc_id in nodes_by_id:
                return
            acc_info = account_store.get(acc_id) or {"account_id": acc_id}
            acc_type = acc_info.get("account_type")
            if not acc_type:
                if acc_id.startswith("ACC-USR") or acc_id.startswith("ACC-VICTIM") or acc_id.startswith("ACC-SRC"):
                    acc_type = "SOURCE"
                elif acc_id.startswith("ACC-MERCH") or acc_id.startswith("CASHOUT") or acc_id.startswith("DESK") or acc_id.startswith("CRYPTO"):
                    acc_type = "DESTINATION"
                elif acc_id.startswith("ACC-COL") or acc_id.startswith("ACC-HUB") or acc_id.startswith("UPI"):
                    acc_type = "INTERMEDIARY"
                else:
                    acc_type = default_type

            nodes_by_id[acc_id] = {
                "account_id": str(acc_id),
                "accountId": str(acc_id),
                "id": str(acc_id),
                "status": acc_info.get("status", "active"),
                "balance": float(acc_info.get("current_balance_sim", 125000.0)),
                "account_type": acc_type,
                "node_type": acc_type.lower(),
                "risk_score": float(acc_info.get("risk_score", 85.0 if acc_type == "MULE" else 20.0))
            }

        def _add_tx_edge(tx_item: dict, is_primary: bool = False):
            tid = tx_item.get("tx_id")
            if not tid or tid in edges_by_tx:
                return
            s = str(tx_item.get("sender_account", ""))
            r = str(tx_item.get("receiver_account", ""))
            if not s or not r:
                return
            _add_account_node(s, "SOURCE" if is_primary else "MULE")
            _add_account_node(r, "DESTINATION" if is_primary else "MULE")
            edges_by_tx[tid] = {
                "id": str(tid),
                "from": s,
                "to": r,
                "source": s,
                "target": r,
                "tx_id": str(tid),
                "amount": float(tx_item.get("amount", 0.0)),
                "hop_number": int(tx_item.get("hop_number", 1)),
                "total_hops": int(tx_item.get("total_hops", 1)),
                "chain_id": tx_item.get("chain_id") or f"CHAIN-{tid[:8]}",
                "pattern_type": tx_item.get("pattern_type") or "STANDARD",
                "suspicious": bool(tx_item.get("risk_score", 0) >= 60 or tx_item.get("is_mule", False)),
                "channel": tx_item.get("channel", "UPI"),
                "parent_transaction_id": tx_item.get("parent_transaction_id"),
                "root_transaction_id": tx_item.get("root_transaction_id") or tid,
                "timestamp": tx_item.get("timestamp", ""),
                "is_primary_path": is_primary
            }

        # 1. Add primary focal transaction
        _add_tx_edge(f_tx, is_primary=True)

        # 2. If part of an explicit chain/root network, add all transactions sharing that chain or root
        if f_cid:
            chain_txs = [t for t in all_txs if t.get("chain_id") == f_cid]
            for c_tx in chain_txs:
                _add_tx_edge(c_tx)

        if f_rid:
            root_txs = [
                t for t in all_txs
                if (t.get("root_transaction_id") == f_rid or t.get("parent_transaction_id") == f_rid)
                and (not f_case or t.get("case_id") == f_case)
            ]
            for r_tx in root_txs:
                _add_tx_edge(r_tx)

        # 3. Connected Component BFS Traversal (up to depth_limit hops)
        depth_limit = min(max(1, max_depth), MAX_GRAPH_HOPS)
        current_connected_accounts = set(nodes_by_id.keys())

        for _ in range(depth_limit):
            found_new = False
            for t in all_txs:
                tid = t.get("tx_id")
                if not tid or tid in edges_by_tx:
                    continue
                s = str(t.get("sender_account", ""))
                r = str(t.get("receiver_account", ""))
                is_touching = (s in current_connected_accounts or r in current_connected_accounts)
                if not is_touching:
                    continue

                case_match = (f_case and t.get("case_id") == f_case)
                chain_match = (f_cid and t.get("chain_id") == f_cid)
                # Check root or parent linkage bidirectionally
                link_match = bool(
                    (t.get("parent_transaction_id") in edges_by_tx) or 
                    (t.get("root_transaction_id") and t.get("root_transaction_id") == f_rid) or
                    (any(e.get("parent_transaction_id") == tid for e in edges_by_tx.values()))
                )

                if case_match or chain_match or link_match:
                    _add_tx_edge(t)
                    if s:
                        current_connected_accounts.add(s)
                    if r:
                        current_connected_accounts.add(r)
                    found_new = True

            if not found_new:
                break

        # Strictly authentic data: no disconnected sibling stuffing!
        final_edges = list(edges_by_tx.values())
        final_edges.sort(key=lambda e: (e.get("hop_number", 1), e.get("timestamp", "")))

        active_node_ids = set()
        for e in final_edges:
            active_node_ids.add(e.get("from"))
            active_node_ids.add(e.get("to"))

        final_nodes = [n for n in nodes_by_id.values() if (n.get("account_id") or n.get("id")) in active_node_ids]
        graph = {
            "nodes": final_nodes,
            "edges": final_edges,
            "primary_tx_id": focus_tx_id,
            "case_id": f_case,
            "chain_id": f_cid
        }
        _recalculate_node_stats(graph)
        graph["topology_type"] = classify_topology_archetype(graph)
        return graph

    # Otherwise build case graph
    existing_graph = store["graphs"].get(case_id, {"nodes": [], "edges": []})
    nodes_by_id = {n.get("account_id") or n.get("id"): n for n in existing_graph.get("nodes", [])}
    edges_by_tx = {e.get("tx_id"): e for e in existing_graph.get("edges", [])}

    depth_limit = min(max(1, max_depth), MAX_GRAPH_HOPS)
    target_chain_ids = set()
    target_root_txs = set()

    case_tx_ids = set(case_obj.get("transactions", []))
    seed_accounts = set(case_obj.get("chain", []))
    if case_obj.get("origin_account"):
        seed_accounts.add(case_obj.get("origin_account"))

    for e in existing_graph.get("edges", []):
        if e.get("from"):
            seed_accounts.add(e.get("from"))
        if e.get("to"):
            seed_accounts.add(e.get("to"))
        if e.get("chain_id"):
            target_chain_ids.add(e.get("chain_id"))
        if e.get("root_transaction_id"):
            target_root_txs.add(e.get("root_transaction_id"))

    visited_accounts = set(seed_accounts)
    current_frontier = set(seed_accounts)
    collected_txs = {}

    for tx in all_txs:
        tid = tx.get("tx_id")
        if not tid:
            continue
        c_id = tx.get("chain_id")
        r_id = tx.get("root_transaction_id")
        case_match = (tx.get("case_id") == case_id) or (tid in case_tx_ids)
        chain_match = (c_id and c_id in target_chain_ids)
        root_match = (r_id and r_id in target_root_txs)

        if case_match or chain_match or root_match:
            collected_txs[tid] = tx
            if c_id:
                target_chain_ids.add(c_id)
            if r_id:
                target_root_txs.add(r_id)
            snd = tx.get("sender_account")
            rcv = tx.get("receiver_account")
            if snd:
                visited_accounts.add(snd)
                current_frontier.add(snd)
            if rcv:
                visited_accounts.add(rcv)
                current_frontier.add(rcv)

    for _ in range(depth_limit):
        if not current_frontier:
            break
        next_frontier = set()
        for tx in all_txs:
            tid = tx.get("tx_id")
            if not tid or tid in collected_txs:
                continue
            snd = tx.get("sender_account")
            rcv = tx.get("receiver_account")
            if snd in current_frontier or rcv in current_frontier:
                collected_txs[tid] = tx
                if snd and snd not in visited_accounts:
                    next_frontier.add(snd)
                    visited_accounts.add(snd)
                if rcv and rcv not in visited_accounts:
                    next_frontier.add(rcv)
                    visited_accounts.add(rcv)
        current_frontier = next_frontier

    for tid, tx in collected_txs.items():
        snd = tx.get("sender_account")
        rcv = tx.get("receiver_account")
        amt = float(tx.get("amount", 0.0))

        if snd and snd not in nodes_by_id:
            acc_info = account_store.get(snd) or {"account_id": snd}
            nodes_by_id[snd] = {
                "account_id": str(snd),
                "accountId": str(snd),
                "id": str(snd),
                "status": acc_info.get("status", "active"),
                "balance": float(acc_info.get("current_balance_sim", 0.0)),
                "account_type": acc_info.get("account_type") or ("SOURCE" if snd.startswith("ACC-USR") else "MULE"),
                "risk_score": float(acc_info.get("risk_score", 0.0))
            }

        if rcv and rcv not in nodes_by_id:
            acc_info = account_store.get(rcv) or {"account_id": rcv}
            nodes_by_id[rcv] = {
                "account_id": str(rcv),
                "accountId": str(rcv),
                "id": str(rcv),
                "status": acc_info.get("status", "active"),
                "balance": float(acc_info.get("current_balance_sim", 0.0)),
                "account_type": acc_info.get("account_type") or ("DESTINATION" if rcv.startswith("ACC-MERCH") else "MULE"),
                "risk_score": float(acc_info.get("risk_score", 0.0))
            }

        if tid not in edges_by_tx:
            edges_by_tx[tid] = {
                "id": str(tid),
                "from": str(snd),
                "to": str(rcv),
                "source": str(snd),
                "target": str(rcv),
                "tx_id": str(tid),
                "amount": amt,
                "hop_number": int(tx.get("hop_number", 1)),
                "total_hops": int(tx.get("total_hops", 1)),
                "chain_id": tx.get("chain_id") or f"CHAIN-{str(tid)[:8]}",
                "pattern_type": tx.get("pattern_type") or "STANDARD",
                "suspicious": bool(tx.get("risk_score", 0) >= 70 or tx.get("is_mule", False)),
                "channel": tx.get("channel", "UPI"),
                "parent_transaction_id": tx.get("parent_transaction_id"),
                "root_transaction_id": tx.get("root_transaction_id") or tid,
                "timestamp": tx.get("timestamp", ""),
                "risk_score": float(tx.get("risk_score", 0.0))
            }

    final_edges = list(edges_by_tx.values())
    if len(final_edges) > depth_limit:
        final_edges = final_edges[:depth_limit]
    active_node_ids = set()
    for e in final_edges:
        active_node_ids.add(e.get("from"))
        active_node_ids.add(e.get("to"))

    final_nodes = [n for n in nodes_by_id.values() if (n.get("account_id") or n.get("id")) in active_node_ids]
    if not final_nodes and nodes_by_id:
        final_nodes = list(nodes_by_id.values())

    graph = {"nodes": final_nodes, "edges": final_edges, "case_id": case_id}

    store["graphs"][case_id] = graph
    _recalculate_node_stats(graph)
    graph["topology_type"] = classify_topology_archetype(graph)
    return graph
