import copy
import random
from app.engines.scoring_engine import score_transaction
from app.engines.case_manager import process_scored_tx
from app.engines.graph_engine import add_node, add_edge, get_graph
from app.engines.recovery_engine import recalculate
from app.services.reasoning_engine import generate_reasoning
from app.services.ml_risk_engine import predict_ml_score, feature_names

def run_pipeline(tx: dict, store: dict, read_only: bool = False) -> dict:
    """
    Main integration pipeline processing a single transaction
    through all core SENTINEL engines sequentially.
    
    When read_only is True (or for benchmark sources), state mutations to
    accounts, cases, graphs, transactions, and action executions are prevented.
    """
    is_read_only = bool(
        read_only
        or tx.get("benchmark_run_id")
        or tx.get("source") in ("BENCHMARK_LAB", "MANUAL_CUSTOM_INPUT")
    )
    
    # FIX 4: Safe Graph Initialization
    if "graphs" not in store and not is_read_only:
        store["graphs"] = {}
        
    # FIX 3: Safe Account Fallback & Persistence
    sender_id = tx.get("sender_account")
    if "accounts" not in store and not is_read_only:
        store["accounts"] = {}
    
    def _determine_kyc_status(acc_id: str, default: str = "PENDING") -> str:
        if not acc_id:
            return default
        upper = acc_id.upper()
        if upper.startswith("ACC-USR") or upper.startswith("ACC-MERCH") or upper.startswith("ACC-REGULAR"):
            return "VERIFIED"
        elif upper.startswith("ACC-EXIT"):
            return "UNVERIFIED"
        elif upper.startswith("ACC-MULE") or upper.startswith("ACC-HUB") or upper.startswith("ACC-LAYER"):
            return "PENDING"
        return default

    existing_account = store.get("accounts", {}).get(sender_id)
    if not existing_account:
        # Determine if is_new_receiver is specified in tx or simulator_meta
        sim_meta_new = tx.get("simulator_meta", {}).get("is_new_receiver")
        is_new_val = bool(sim_meta_new) if sim_meta_new is not None else bool(tx.get("is_new_receiver", True))
        account = {
            "account_id": sender_id,
            "avg_monthly_tx_amount": float(tx.get("avg_monthly_tx_amount", 25000.0)),
            "current_balance_sim": 150000.0,
            "status": "active",
            "kyc_status": _determine_kyc_status(sender_id, "PENDING"),
            "is_new_receiver": is_new_val,
        }
        if not is_read_only:
            store.setdefault("accounts", {})[sender_id] = account
    else:
        account = copy.deepcopy(existing_account) if is_read_only else existing_account
        if "kyc_status" not in account:
            account["kyc_status"] = _determine_kyc_status(sender_id, "PENDING")
        # Preserve is_new_receiver if explicitly given in simulator_meta or tx
        if "simulator_meta" in tx and "is_new_receiver" in tx["simulator_meta"]:
            account["is_new_receiver"] = bool(tx["simulator_meta"]["is_new_receiver"])
        elif "is_new_receiver" in tx:
            account["is_new_receiver"] = bool(tx["is_new_receiver"])
        elif not is_read_only and "is_new_receiver" not in account:
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
        seed = tx.get("benchmark_seed")
        if not seed and (tx.get("benchmark_run_id") or tx.get("source") in ("BENCHMARK_LAB", "MANUAL_CUSTOM_INPUT")):
            seed = f"{tx.get('benchmark_run_id', 'BM')}:{tx.get('tx_id', '')}"

        ml_score = predict_ml_score(float(rule_score), seed=seed)
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
        rnd_gen = _rnd.Random(seed) if seed is not None else _rnd
        importance = {fn: round(1/len(feature_names) + rnd_gen.uniform(-0.02, 0.02), 4)
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


    # 4. Call case_manager (only in live mode)
    case = None
    graph = None
    recovery = None

    if not is_read_only:
        case = process_scored_tx(tx, score_output, store)
        
        # FIX 1: ORIGIN SCORE PERSISTENCE (Moved after process_scored_tx)
        if tx.get("hop_number", 0) == 0:
            tx["origin_score"] = tx.get("risk_score", 0)
            if case:
                case["origin_score"] = tx.get("risk_score", 0)
        
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
                    "status": "withdrawn" if (receiver_id and receiver_id.startswith("ACC-EXIT")) else "active",
                    "kyc_status": _determine_kyc_status(receiver_id, "PENDING")
                }
                if receiver_id:
                    store.setdefault("accounts", {})[receiver_id] = receiver_account
            elif "kyc_status" not in receiver_account:
                receiver_account["kyc_status"] = _determine_kyc_status(receiver_id, "PENDING")
                
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
    else:
        # In read-only / benchmark mode, keep origin score without modifying store
        if tx.get("hop_number", 0) == 0 and "origin_score" not in tx:
            tx["origin_score"] = tx.get("risk_score", 0)

    # 7. Evaluate Automated Response Policy & Phase 16 Autonomous Action Executor
    automate_mode = bool(store.get("automation_mode", False))
    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy

    policy_decision = evaluate_autonomous_policy(
        tx=tx,
        case=case,
        automate_mode=automate_mode
    )

    if is_read_only:
        requires_operator = (policy_decision.get("action") == "FREEZE")
        execution_record = {
            "execution_status": "REQUIRES_OPERATOR_ACTION" if requires_operator else "SIMULATED_SUCCESS",
            "actor_type": "HUMAN_OPERATOR" if requires_operator else "AUTOMATION_ENGINE",
            "action_code": policy_decision.get("action", "MONITOR"),
            "policy_decision": policy_decision,
            "simulated": True,
            "boundary_enforced": True,
        }
    else:
        from app.services.simulated_action_executor import execute_simulated_action
        import asyncio

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

    # 8. Store transaction globally (only in live mode)
    if not is_read_only:
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

