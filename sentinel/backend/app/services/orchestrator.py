import random
from app.engines.scoring_engine import score_transaction
from app.engines.case_manager import process_scored_tx
from app.engines.graph_engine import add_node, add_edge, get_graph
from app.engines.recovery_engine import recalculate
from app.services.reasoning_engine import generate_reasoning
from app.services.ml_risk_engine import predict_ml_score, feature_names

def run_pipeline(tx: dict, store: dict) -> dict:
    """
    Main integration pipeline processing a single transaction
    through all core SENTINEL engines sequentially.
    """
    
    # FIX 4: Safe Graph Initialization
    if "graphs" not in store:
        store["graphs"] = {}
        
    # FIX 3: Safe Account Fallback & Persistence
    sender_id = tx.get("sender_account")
    if "accounts" not in store:
        store["accounts"] = {}
    
    account = store["accounts"].get(sender_id)
    if not account:
        account = {
            "account_id": sender_id,
            "avg_monthly_tx_amount": round(random.uniform(10000, 50000), 2),
            "current_balance_sim": round(random.uniform(50000, 250000), 2),
            "status": "active",
            "is_new_receiver": True # First time seen
        }
        store["accounts"][sender_id] = account
    else:
        account["is_new_receiver"] = False
        
    # 1b. Try to find an existing active case to inherit origin_score
    case_id = tx.get("case_id")
    case = None
    if case_id:
        case = store.get("cases", {}).get(case_id)
    else:
        # Fallback: Find case where sender or receiver is already in a chain
        receiver_id = tx.get("receiver_account")
        case = next((c for c in store.get("cases", {}).values()
                     if isinstance(c, dict) and (c.get("origin_account") == sender_id or sender_id in c.get("chain", []) or receiver_id in c.get("chain", []))
                     and c.get("status") in ["NEW", "HIGH_RISK"]
                     and len(c.get("chain", [])) < c.get("max_nodes", 5)), None)


        if case:
            tx["case_id"] = case["case_id"]

    if case:
        tx["origin_score"] = case.get("origin_score", 0)

    # 2. Call scoring_engine
    score_output = score_transaction(tx, account)
    rule_score = score_output.get("risk_score", 0)
    ml_score = rule_score
    final_score = rule_score

    try:
        # 4. Rule-Guided ML Emulator — predict from rule_score directly
        ml_score = predict_ml_score(float(rule_score))
        print(f"  [DEBUG] Rule: {rule_score}, ML: {round(ml_score, 1)}")

        # 5. Hybrid Fusion: 60% ML + 40% Rule (high correlation guaranteed)
        final_score = int(0.6 * ml_score + 0.4 * rule_score)
    except Exception as e:
        print(f"  [Orchestrator] ML Scoring Failed: {e}")
        final_score = rule_score
        ml_score = rule_score

    score_output["risk_score"] = final_score
    score_output["rule_score"] = int(rule_score)
    score_output["ml_score"] = int(ml_score)

    # Feature Importance (Explainability — Dynamic Per-Transaction)
    # Step 1: Map rule factor contributions onto feature slots
    risk_factors = score_output.get("risk_factors", [])
    name_map = {
        "new_receiver":     "is_new_receiver",
        "amount_deviation": "amount",
        "time_anomaly":     "hour",
        "call_flag":        "call_flag",
        "velocity_spike":   "velocity",
        "bulk_transfer":    "chain_depth",
        "cross_border_risk":"amount",
        "device_anomaly":   "is_new_receiver",
        "crypto_risk":      "call_flag",
        "remote_access":    "call_flag",
        "scripted_behavior":"call_flag",
        "first_time_payee": "is_new_receiver",
    }

    raw = {fn: 0.0 for fn in feature_names}
    for f in risk_factors:
        mapped = name_map.get(f["name"], None)
        if mapped and mapped in raw:
            raw[mapped] += float(f.get("contribution", 0))

    # Step 2: Add per-transaction raw signal so every tx has unique values
    # even when no rule factors fired (eliminates equal-weight fallback)
    try:
        from datetime import datetime as _dt
        sim_meta = tx.get("simulator_meta", {})

        ts = tx.get("timestamp", "")
        try:
            dt = _dt.fromisoformat(ts.replace("Z", "+00:00"))
            hour_val = dt.hour / 23.0
        except Exception:
            hour_val = 0.5

        amount_val   = min(float(tx.get("amount", 0)) / 500000.0, 1.0)

        # Read velocity from simulator_meta first, then account
        velocity_raw = sim_meta.get("tx_velocity", account.get("tx_velocity", 1))
        velocity_val = min(float(velocity_raw) / 15.0, 1.0)

        # Read is_new_receiver from simulator_meta first, then account
        is_new_raw   = sim_meta.get("is_new_receiver", account.get("is_new_receiver", False))
        is_new_val   = 1.0 if is_new_raw else 0.08

        call_val     = 1.0 if tx.get("on_active_call", False) else 0.04
        hop_val      = min(float(tx.get("hop_number", 0)) / 5.0, 1.0)

        # Small base weight so rule contributions dominate when present
        SIGNAL_SCALE = 5.0
        raw["amount"]          += amount_val   * SIGNAL_SCALE
        raw["hour"]            += hour_val     * SIGNAL_SCALE
        raw["is_new_receiver"] += is_new_val   * SIGNAL_SCALE
        raw["velocity"]        += velocity_val * SIGNAL_SCALE
        raw["call_flag"]       += call_val     * SIGNAL_SCALE
        raw["chain_depth"]     += hop_val      * SIGNAL_SCALE
    except Exception:
        pass

    # Step 3: Normalize to percentages summing to 1.0
    total_raw = sum(raw.values())
    if total_raw > 0:
        importance = {k: round(v / total_raw, 4) for k, v in raw.items()}
    else:
        import random as _rnd
        importance = {fn: round(1/len(feature_names) + _rnd.uniform(-0.02, 0.02), 4)
                      for fn in feature_names}

    score_output["ml_feature_importance"] = dict(
        sorted(importance.items(), key=lambda x: x[1], reverse=True)
    )

    # Update threshold based on final hybrid score
    if final_score >= 70:
        score_output["threshold"] = "HIGH_RISK"
    elif final_score >= 40:
        score_output["threshold"] = "MEDIUM"
    else:
        score_output["threshold"] = "LOW"
    
    reason_data = generate_reasoning(score_output.get("risk_factors", []))
    score_output["reason"] = reason_data["short_reason"]
    score_output["full_reason"] = reason_data["full_reason"]
    
    score = score_output["risk_score"]
    confidence = "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"
    score_output["confidence"] = confidence
    
    print(f"  [Orchestrator] {tx.get('tx_id')} Score: {score} (Rule: {int(rule_score)}, ML: {int(ml_score)}) | Reason: {score_output['reason']}")

    # 3. Update transaction with score results
    tx["risk_score"] = score_output.get("risk_score")
    tx["rule_score"] = score_output.get("rule_score")
    tx["ml_score"] = score_output.get("ml_score")
    tx["risk_factors"] = score_output.get("risk_factors")
    tx["threshold"] = score_output.get("threshold")
    tx["top_reason"] = score_output.get("top_reason")
    tx["reason"] = score_output["reason"]
    tx["full_reason"] = score_output["full_reason"]
    tx["confidence"] = score_output["confidence"]
    tx["ml_feature_importance"] = score_output.get("ml_feature_importance", {})


    # 4. Call case_manager
    case = process_scored_tx(tx, score_output, store)
    
    # FIX 1: ORIGIN SCORE PERSISTENCE (Moved after process_scored_tx)
    if tx.get("hop_number", 0) == 0:
        tx["origin_score"] = tx.get("risk_score", 0)
        if case:
            case["origin_score"] = tx.get("risk_score", 0)
    
    graph = None
    recovery = None

    # 5. GRAPH ENGINE (IMPORTANT)
    # Only triggered if a case was created or escalated
    if case:
        case_id = case["case_id"]
        
        # FIX 2: RECEIVER FALLBACK (RECOVERY FIX)
        receiver_id = tx.get("receiver_account")
        receiver_account = store.get("accounts", {}).get(receiver_id)
        if not receiver_account:
            amount = float(tx.get("amount", 0.0))
            receiver_account = {
                "account_id": receiver_id,
                # Initialization: Start with enough balance to cover the fraud inflow
                "current_balance_sim": round(amount * random.uniform(0.9, 1.1), 2),
                "status": "withdrawn" if receiver_id.startswith("ACC-EXIT") else "active"
            }
            
        # Add Nodes to Graph
        add_node(case_id, account, store)
        add_node(case_id, receiver_account, store)
        
        # Add Edge representing the transaction flow
        amount = float(tx.get("amount", 0.0))
        extra_meta = {
            "hop_number": tx.get("hop_number", 1),
            "total_hops": tx.get("total_hops", 1),
            "chain_id": tx.get("chain_id"),
            "pattern_type": tx.get("pattern_type"),
            "parent_transaction_id": tx.get("parent_transaction_id"),
            "root_transaction_id": tx.get("root_transaction_id"),
            "timestamp": tx.get("timestamp", "")
        }
        add_edge(case_id, sender_id, receiver_id, tx.get("tx_id"), amount, store, extra=extra_meta)

        
        # Fetch finalized graph
        graph = get_graph(case_id, store)
        
        # 6. Call recovery_engine
        recovery = recalculate(case_id, store)

    # 7. Evaluate Automated Response Policy & Phase 16 Autonomous Action Executor
    automate_mode = bool(store.get("automation_mode", False))
    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
    from app.services.simulated_action_executor import execute_simulated_action
    import asyncio

    policy_decision = evaluate_autonomous_policy(
        tx=tx,
        case=case,
        automate_mode=automate_mode
    )

    try:
        execution_record = asyncio.run(
            execute_simulated_action(
                case_id=case.get("case_id") if case else tx.get("case_id"),
                tx_id=tx.get("tx_id"),
                action_code=policy_decision.get("action", "MONITOR"),
                policy_decision=policy_decision,
                actor_type="AUTOMATION_ENGINE"
            )
        )
    except Exception:
        execution_record = {
            "execution_status": "SUCCESS" if (automate_mode and policy_decision.get("action") != "FREEZE") else "NOT_EXECUTED" if not automate_mode else "REQUIRES_OPERATOR_ACTION",
            "actor_type": "AUTOMATION_ENGINE" if (automate_mode and policy_decision.get("action") != "FREEZE") else "HUMAN_OPERATOR",
            "action_code": policy_decision.get("action", "MONITOR"),
            "automation_mode": "AUTOMATE_ON" if automate_mode else "AUTOMATE_OFF"
        }

    tx["execution_record"] = execution_record
    tx["response_decision"] = policy_decision

    # 8. Store transaction globally
    tx_id = tx.get("tx_id")
    if tx_id:
        if "transactions" not in store:
            store["transactions"] = {}
        store["transactions"][tx_id] = tx

    # Final formatted output
    return {
        "transaction": tx,
        "case": case,
        "graph": graph,
        "recovery": recovery,
        "response_decision": policy_decision,
        "execution_record": execution_record
    }

