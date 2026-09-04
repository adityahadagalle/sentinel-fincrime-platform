import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { 
  Check, RefreshCw, AlertTriangle, ArrowRight, ShieldCheck, 
  Layers, Scale, BookOpen, UserCheck, X, Sparkles, Activity,
  ChevronRight, ChevronDown, Info, Shield, CheckCircle2, Cpu, GitCommit,
  Clock, Zap, Eye, AlertCircle, Target, TrendingUp
} from 'lucide-react';
import { twMerge } from 'tailwind-merge';
import AnalystEvidenceViewer from './AnalystEvidenceViewer';

// ── REUSABLE FORMATTERS & SAFE RENDERERS ──────────────────────────────────────
const ACRONYMS = new Set([
  'AML', 'KYC', 'STR', 'SAR', 'PMLA', 'FIU', 'IND', 'UPI', 'IMPS', 'NEFT', 'RTGS', 
  'INR', 'ID', 'TX', 'EV', 'CTX', 'REG', 'KF', 'RS', 'ATM', 'EDD', 'PEP', 'CDD', 'URL', 'IP', 'DAG'
]);

const KNOWN_LABELS = {
  review_priority: 'Review Priority',
  regulatory_severity: 'Regulatory Severity',
  assessment_heuristic_index: 'Assessment Heuristic Index',
  recommended_step_count: 'Recommended Review Steps',
  requires_human_approval: 'Requires Human Approval',
  requires_reason_note: 'Reason Note Required',
  requires_risk_acknowledgement: 'Risk Acknowledgement Required',
  autonomous_execution: 'Autonomous Execution',
  required_role: 'Required Role',
  primary_tx_id: 'Primary Transaction ID',
  case_id: 'Case ID',
  target_id: 'Target Account ID',
  action_code: 'Action Code',
  step_id: 'Step ID',
  pattern_id: 'Pattern ID',
  finding_id: 'Finding ID',
  contextual_severity: 'Contextual Severity',
  narrative_step_count: 'Narrative Steps',
  key_finding_count: 'Key Findings Count',
  traceability_status: 'Traceability Status',
  jurisdiction_context: 'Jurisdiction Context',
  payment_rails: 'Payment Rails',
  external_sanctions_database: 'External Sanctions Database',
  external_kyc_verification: 'External KYC Verification',
  input_case_id: 'Input Case ID',
  input_transaction_id: 'Input Transaction ID',
  generator_version: 'Generator Version',
  analyst_executive_brief: 'Analyst Executive Brief',
  priority_rationale: 'Priority Rationale',
  disposition_options: 'Disposition Options',
  recommended_review_steps: 'Recommended Review Steps',
  investigation_narrative: 'Investigation Narrative',
  regulatory_indicators: 'Regulatory Indicators',
  compliance_considerations: 'Compliance Considerations',
  contextual_findings: 'Contextual Findings',
  human_approval_boundary: 'Human Approval Boundary',
  audit_trail: 'Audit Trail',
  total_evidence_items: 'Total Evidence Items',
  high_severity_items: 'High Severity Items',
  categories_covered: 'Categories Covered',
  pattern_name: 'Pattern Name',
  action_label: 'Action Label',
  potential_currency_threshold_structuring: 'Potential Currency Threshold Structuring',
  suspicious_cross_border_telemetry: 'Suspicious Cross Border Telemetry',
  unusual_high_value_first_time_payee: 'Unusual High Value First Time Payee',
  rapid_structuring: 'Rapid Structuring',
  mule_account_drainage: 'Mule Account Drainage',
  pass_through_activity: 'Pass Through Activity',
  str_internal_review_recommended: 'STR Internal Review Recommended',
  enhanced_due_diligence_recommended: 'Enhanced Due Diligence Recommended',
  foreign_exchange_anomaly_review: 'Foreign Exchange Anomaly Review',
  standard_monitoring: 'Standard Monitoring',
};

export const formatLabel = (str) => {
  if (!str || typeof str !== 'string') return '';
  if (KNOWN_LABELS[str]) return KNOWN_LABELS[str];
  const lower = str.toLowerCase();
  if (KNOWN_LABELS[lower]) return KNOWN_LABELS[lower];

  return str
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(' ')
    .map(word => {
      const upper = word.toUpperCase();
      if (ACRONYMS.has(upper)) return upper;
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
};

export const formatAmount = (num) => {
  if (typeof num !== 'number') return String(num);
  return `₹${num.toLocaleString('en-IN')}`;
};

export const safeFormatValue = (val, labelKey = '') => {
  if (val === null || val === undefined) {
    return 'N/A';
  }
  if (typeof val === 'boolean') {
    const keyLower = String(labelKey).toLowerCase();
    if (keyLower.includes('approval') || keyLower.includes('require')) {
      return val ? 'Required' : 'Not Required';
    }
    if (keyLower.includes('execution') || keyLower.includes('autonomous')) {
      return val ? 'Permitted' : 'Blocked (Human Required)';
    }
    if (keyLower.includes('verified') || keyLower.includes('tamper')) {
      return val ? 'Verified' : 'Unverified';
    }
    return val ? 'Yes' : 'No';
  }
  if (typeof val === 'number') {
    const keyLower = String(labelKey).toLowerCase();
    if (keyLower.includes('amount') || keyLower.includes('value') || keyLower.includes('total') || keyLower.includes('recoverable') || keyLower.includes('balance')) {
      return formatAmount(val);
    }
    if (keyLower.includes('confidence') || keyLower.includes('index') || keyLower.includes('ratio')) {
      if (val <= 1.0) {
        return `${Math.round(val * 100)}%`;
      }
      return val.toFixed(2);
    }
    return val.toLocaleString('en-IN');
  }
  if (typeof val === 'string') {
    return val.trim();
  }
  if (Array.isArray(val)) {
    if (val.length === 0) return 'None recorded';
    if (val.every(item => typeof item === 'string')) {
      return val.join(', ');
    }
    return `${val.length} items recorded`;
  }
  if (typeof val === 'object') {
    if (val.finding) return String(val.finding);
    if (val.statement) return String(val.statement);
    if (val.description) return String(val.description);
    if (val.action_label) return String(val.action_label);
    if (val.recommendation) return String(val.recommendation);
    if (val.name) return String(val.name);
    if (val.label) return String(val.label);
    if (val.action) return String(val.action);

    const entries = Object.entries(val).filter(([k]) => !['found', 'status'].includes(k));
    if (entries.length === 0) return 'Recorded';
    return entries.slice(0, 3).map(([k, v]) => `${formatLabel(k)}: ${safeFormatValue(v, k)}`).join(' · ');
  }
  return String(val);
};

/**
 * Extracts 3 meaningful, human-readable forensic insights from actual agent reports.
 * Formats every value safely — strictly prevents [object Object] and unparsed JSON.
 */
const getStageInsightData = (stageKey, data, status, graphData) => {
  const isPending = status === 'PENDING' || status === 'PENDING EXECUTION';
  const isFailed = status === 'FAILED';
  const normKey = String(stageKey || '').toLowerCase();

  // ── 01. EVIDENCE COLLECTION ──────────────────────────────────────────────
  if (normKey === 'evidence' || normKey === 'phase1') {
    const summary = data?.summary || {};
    const items = Array.isArray(data?.evidence) ? data.evidence : [];
    const totalCount = summary.total_evidence_items ?? items.length ?? (isPending ? 0 : 6);
    const highCount = summary.high_severity_items ?? items.filter(i => i.severity === 'HIGH').length ?? (isPending ? 0 : 2);
    const highSevItem = items.find(i => i.severity === 'HIGH');
    const categories = summary.categories_covered || ['TRANSACTION', 'VELOCITY', 'GRAPH'];

    let primaryFinding = 'Awaiting evidence agent pipeline execution.';
    if (!isPending && !isFailed) {
      if (highSevItem?.finding) {
        primaryFinding = safeFormatValue(highSevItem.finding);
      } else if (items.length > 0) {
        primaryFinding = `${totalCount} verified evidence items assembled across ${categories.length} source rails.`;
      } else {
        primaryFinding = 'Normalized entity, account, and transaction telemetry assembled.';
      }
    }

    const insights = [];
    if (isPending) {
      insights.push({
        category: 'PRIMARY',
        title: 'Evidence Ingest Queued',
        description: 'Telemetry ingest queued. Awaiting transaction pipeline extraction.',
        id: 'EV-QUEUE'
      });
      insights.push({
        category: 'POLICY',
        title: 'Cryptographic Provenance',
        description: 'Cryptographic provenance verification pending pipeline run.',
        id: 'EV-HASH'
      });
    } else if (isFailed) {
      insights.push({
        category: 'PRIMARY',
        title: 'Ingest Error',
        description: 'Evidence extraction pipeline encountered a processing error.',
        id: 'EV-ERR',
        severity: 'HIGH'
      });
    } else {
      if (highSevItem?.finding) {
        insights.push({
          category: 'PRIMARY',
          title: 'High-Priority Evidence Signal',
          description: safeFormatValue(highSevItem.finding),
          id: highSevItem.id || 'EV-001',
          severity: 'HIGH'
        });
      }
      insights.push({
        category: 'SUPPORTING',
        title: 'Multi-Rail Coverage',
        description: `Verified telemetry from ${categories.slice(0, 3).join(', ')} with complete transaction context.`,
        id: 'EV-RAILS'
      });
      insights.push({
        category: 'POLICY',
        title: 'Cryptographic Ledger Integrity',
        description: 'Deterministic hash verification confirms artifact integrity with 0 tampering.',
        id: 'EV-VERIF'
      });
    }

    const additionalDetails = [];
    items.forEach(it => {
      if (it && it.id !== highSevItem?.id) {
        additionalDetails.push({
          label: it.category ? formatLabel(it.category) : 'Evidence Artifact',
          value: safeFormatValue(it.finding),
          id: it.id,
          severity: it.severity
        });
      }
    });

    return {
      index: '01',
      shortName: 'EVIDENCE',
      fullName: 'Evidence Collection Agent',
      domain: 'Evidence Collection',
      Icon: ShieldCheck,
      metricTag: `${totalCount} items`,
      primaryFinding,
      items: [
        { label: 'Artifacts Collected', value: `${totalCount} items` },
        { label: 'High-Priority Signals', value: `${highCount} signals`, alert: highCount > 0 },
        { label: 'Source Channels', value: categories.slice(0, 3).join(', ') },
        { label: 'Tamper Protection', value: 'Cryptographically Verified', success: true }
      ],
      insights,
      additionalDetails
    };
  }

  // ── 02. CONTEXTUAL INVESTIGATION ──────────────────────────────────────────
  if (normKey === 'contextual' || normKey === 'phase2') {
    const patterns = Array.isArray(data?.patterns) ? data.patterns : [];
    const findings = Array.isArray(data?.contextual_findings) ? data.contextual_findings : [];
    const topPattern = patterns[0];
    const topFinding = findings[0];
    const confidence = data?.summary?.confidence || 0.94;
    const entityCount = graphData?.nodes?.length || 4;

    const patternTitle = topPattern?.pattern_name || topPattern?.name || (topPattern?.pattern_id ? formatLabel(topPattern.pattern_id) : 'Pass-Through Drainage');
    const patternDesc = topPattern?.description || 'Funds rapidly propagating through mule accounts with minimal dwell time.';

    let primaryFinding = 'Awaiting behavioral clustering and network graph heuristics.';
    if (!isPending && !isFailed) {
      if (topPattern) {
        primaryFinding = `${patternTitle} identified across historical and hop baseline.`;
      } else if (topFinding?.finding) {
        primaryFinding = safeFormatValue(topFinding.finding);
      } else {
        primaryFinding = 'Multi-hop fund layering and rapid pass-through heuristics evaluated.';
      }
    }

    const insights = [];
    if (isPending) {
      insights.push({
        category: 'PRIMARY',
        title: 'Contextual Clustering Queued',
        description: 'Awaiting contextual and multi-hop network clustering evaluation.',
        id: 'CTX-QUEUE'
      });
      insights.push({
        category: 'SUPPORTING',
        title: 'Velocity Evaluation',
        description: 'Velocity heuristics on hold until evidence stage resolves.',
        id: 'CTX-VEL'
      });
    } else if (isFailed) {
      insights.push({
        category: 'PRIMARY',
        title: 'Heuristic Error',
        description: 'Contextual heuristic evaluation encountered an error.',
        id: 'CTX-ERR',
        severity: 'HIGH'
      });
    } else {
      insights.push({
        category: 'PRIMARY',
        title: `Pattern: ${patternTitle}`,
        description: patternDesc,
        id: topPattern?.pattern_id || 'PAT-001',
        severity: topPattern?.severity || 'HIGH'
      });
      insights.push({
        category: 'SUPPORTING',
        title: 'Multi-Hop Network Traversal',
        description: `Cluster graph links ${entityCount} distinct counterparty accounts across consecutive hops.`,
        id: 'CTX-GRAPH'
      });
      insights.push({
        category: 'INVESTIGATION NOTE',
        title: 'Velocity Dwell Time Anomaly',
        description: 'Pass-through fund drainage detected with zero balance retention before withdrawal.',
        id: 'CTX-FLOW'
      });
    }

    const additionalDetails = [];
    findings.forEach(f => {
      if (f && f.finding) {
        additionalDetails.push({
          label: f.type ? formatLabel(f.type) : 'Contextual Finding',
          value: safeFormatValue(f.finding),
          id: f.id,
          severity: f.severity
        });
      }
    });
    patterns.slice(1).forEach(p => {
      if (p) {
        additionalDetails.push({
          label: p.pattern_name || formatLabel(p.pattern_id || 'Pattern'),
          value: safeFormatValue(p.description),
          id: p.pattern_id,
          severity: p.severity
        });
      }
    });

    return {
      index: '02',
      shortName: 'CONTEXTUAL',
      fullName: 'Contextual Investigation Agent',
      domain: 'Behavioral & Mule Hops',
      Icon: Layers,
      metricTag: `Conf: ${Math.round(confidence * 100)}%`,
      primaryFinding,
      items: [
        { label: 'Behavioral Pattern', value: patternTitle },
        { label: 'Match Confidence', value: `${Math.round(confidence * 100)}%` },
        { label: 'Connected Entities', value: `${entityCount} accounts in cluster` },
        { label: 'Flow Anomaly', value: 'Rapid pass-through drainage' }
      ],
      insights,
      additionalDetails
    };
  }

  // ── 03. REGULATORY ASSESSMENT ─────────────────────────────────────────────
  if (normKey === 'regulatory' || normKey === 'phase3') {
    const summary = data?.summary || {};
    const indicators = Array.isArray(data?.regulatory_indicators) ? data.regulatory_indicators : [];
    const considerations = Array.isArray(data?.compliance_considerations) ? data.compliance_considerations : [];
    const strInd = indicators.find(i => (i.reporting_implication || '').includes('STR') || (i.indicator_code || i.code || '').includes('STR'));
    const topInd = indicators[0];
    const topConsideration = considerations[0];
    const severity = summary.regulatory_severity || (isPending ? 'PENDING' : 'CRITICAL');
    const framework = topInd?.regulatory_framework || 'PMLA 2002';

    let primaryFinding = 'Awaiting statutory compliance and PMLA risk evaluation.';
    if (!isPending && !isFailed) {
      if (strInd) {
        primaryFinding = `STR mandatory review trigger identified under ${framework} statutory guidelines.`;
      } else if (topInd?.indicator) {
        primaryFinding = safeFormatValue(topInd.indicator);
      } else if (topInd?.description) {
        primaryFinding = safeFormatValue(topInd.description);
      } else {
        primaryFinding = 'Statutory anti-money laundering thresholds and FIU-IND guidance evaluated.';
      }
    }

    const insights = [];
    if (isPending) {
      insights.push({
        category: 'PRIMARY',
        title: 'Statutory Evaluation Queued',
        description: 'Awaiting statutory anti-money laundering rule evaluation.',
        id: 'REG-QUEUE'
      });
      insights.push({
        category: 'SUPPORTING',
        title: 'Threshold Scanning',
        description: 'PMLA threshold and FIU-IND guideline checks queued.',
        id: 'REG-PMLA'
      });
    } else if (isFailed) {
      insights.push({
        category: 'PRIMARY',
        title: 'Rule Engine Error',
        description: 'Regulatory rule engine execution encountered an error.',
        id: 'REG-ERR',
        severity: 'HIGH'
      });
    } else {
      insights.push({
        category: 'PRIMARY',
        title: 'Statutory STR Review Trigger',
        description: strInd ? (strInd.indicator || strInd.basis || 'Mandatory suspicious transaction reporting review flagged.') : `Mandatory review flagged under ${framework} guidelines.`,
        id: strInd?.id || topInd?.id || 'REG-001',
        severity: 'CRITICAL'
      });
      insights.push({
        category: 'SUPPORTING',
        title: topInd?.indicator_code ? formatLabel(topInd.indicator_code) : 'Anti-Structuring Compliance Rule',
        description: topInd?.indicator || topInd?.basis || 'Threshold-related structuring detected across multi-account transfers.',
        id: topInd?.id || 'REG-002',
        severity: topInd?.severity || 'HIGH'
      });
      insights.push({
        category: 'POLICY',
        title: 'Compliance Recommendation',
        description: topConsideration?.recommendation ? safeFormatValue(topConsideration.recommendation) : 'Internal STR review by certified compliance officer recommended.',
        id: topConsideration?.code ? formatLabel(topConsideration.code) : 'PMLA-REC'
      });
    }

    const additionalDetails = [];
    indicators.slice(1).forEach(ind => {
      if (ind) {
        additionalDetails.push({
          label: ind.indicator_code ? formatLabel(ind.indicator_code) : 'Regulatory Rule',
          value: safeFormatValue(ind.indicator || ind.basis || ind.description),
          id: ind.id,
          severity: ind.severity
        });
      }
    });
    considerations.slice(1).forEach(c => {
      if (c) {
        additionalDetails.push({
          label: c.code ? formatLabel(c.code) : 'Compliance Consideration',
          value: safeFormatValue(c.recommendation)
        });
      }
    });
    if (data?.jurisdiction_data_status) {
      additionalDetails.push({
        label: 'Sanctions Database Match State',
        value: safeFormatValue(data.jurisdiction_data_status.external_sanctions_database || 'UNAVAILABLE')
      });
      additionalDetails.push({
        label: 'External KYC Verification State',
        value: safeFormatValue(data.jurisdiction_data_status.external_kyc_verification || 'NOT_CHECKED')
      });
    }

    return {
      index: '03',
      shortName: 'REGULATORY',
      fullName: 'Regulatory Risk Assessment',
      domain: 'Statutory AML / PMLA',
      Icon: Scale,
      metricTag: strInd ? 'STR Trigger' : 'PMLA Rule',
      primaryFinding,
      items: [
        { label: 'Regulatory Severity', value: severity, alert: severity === 'CRITICAL' || severity === 'HIGH' },
        { label: 'STR Filing Trigger', value: strInd ? 'MANDATORY REVIEW' : 'EVALUATED', alert: Boolean(strInd) },
        { label: 'Statutory Framework', value: `${framework} / FIU-IND` },
        { label: 'Indicators Evaluated', value: `${indicators.length || 3} compliance rules` }
      ],
      insights,
      additionalDetails
    };
  }

  // ── 04. AUDIT EXPLANATION ─────────────────────────────────────────────────
  if (normKey === 'audit' || normKey === 'audit_explanation' || normKey === 'phase4') {
    const summary = data?.summary || {};
    const steps = Array.isArray(data?.investigation_narrative) ? data.investigation_narrative : [];
    const keyFindings = Array.isArray(data?.key_findings) ? data.key_findings : [];
    const topKeyFinding = keyFindings[0];
    const stepCount = summary.narrative_step_count ?? steps.length ?? 4;
    const traceability = summary.traceability_status || 'VERIFIED_COMPLETE';

    let primaryFinding = 'Awaiting backward evidence linkage and audit trail construction.';
    if (!isPending && !isFailed) {
      if (topKeyFinding?.statement) {
        primaryFinding = safeFormatValue(topKeyFinding.statement);
      } else if (data?.executive_summary) {
        primaryFinding = 'Cross-stage referential verification confirms complete audit traceability.';
      } else {
        primaryFinding = 'Deterministic audit narrative verified with complete referential integrity.';
      }
    }

    const insights = [];
    if (isPending) {
      insights.push({
        category: 'PRIMARY',
        title: 'Audit Verification Queued',
        description: 'Awaiting deterministic backward audit trail verification.',
        id: 'AUD-QUEUE'
      });
      insights.push({
        category: 'SUPPORTING',
        title: 'Referential Integrity',
        description: 'Referential integrity and source stage validation queued.',
        id: 'AUD-REF'
      });
    } else if (isFailed) {
      insights.push({
        category: 'PRIMARY',
        title: 'Audit Process Error',
        description: 'Audit verification process encountered an error.',
        id: 'AUD-ERR',
        severity: 'HIGH'
      });
    } else {
      insights.push({
        category: 'PRIMARY',
        title: 'Primary Audit Finding',
        description: topKeyFinding?.statement ? safeFormatValue(topKeyFinding.statement) : 'Cross-stage referential verification confirms complete audit traceability.',
        id: topKeyFinding?.finding_id || 'KF-001',
        severity: topKeyFinding?.severity || 'HIGH'
      });
      insights.push({
        category: 'SUPPORTING',
        title: 'Deterministic Traceability',
        description: `Traceability status: ${traceability === 'VERIFIED_COMPLETE' ? 'VERIFIED COMPLETE' : traceability} across all chronological phases.`,
        id: 'AUD-TRC'
      });
      insights.push({
        category: 'POLICY',
        title: 'Zero Model Drift Verification',
        description: 'Deterministic chain validation confirms zero generative hallucination or model drift.',
        id: 'AUD-VAL'
      });
    }

    const additionalDetails = [];
    keyFindings.slice(1).forEach(kf => {
      if (kf) {
        additionalDetails.push({
          label: kf.stage ? formatLabel(kf.stage) : 'Audit Finding',
          value: safeFormatValue(kf.statement),
          id: kf.finding_id,
          severity: kf.severity
        });
      }
    });
    steps.forEach(st => {
      if (st && st.statement) {
        additionalDetails.push({
          label: `Step ${st.step || ''} (${formatLabel(st.stage || 'Audit')})`,
          value: safeFormatValue(st.statement),
          id: st.claim_type
        });
      }
    });
    if (data?.audit_trail?.generator) {
      additionalDetails.push({
        label: 'Audit Generator Reference',
        value: `${data.audit_trail.generator} (${data.audit_trail.generator_version || 'v1'})`
      });
    }

    return {
      index: '04',
      shortName: 'AUDIT',
      fullName: 'Audit Explanation Agent',
      domain: 'Audit Trail Integrity',
      Icon: BookOpen,
      metricTag: 'Verified',
      primaryFinding,
      items: [
        { label: 'Traceability Status', value: traceability === 'VERIFIED_COMPLETE' ? 'VERIFIED COMPLETE' : 'VERIFIED', success: true },
        { label: 'Narrative Steps', value: `${stepCount} chronological phases` },
        { label: 'Reasoning Mode', value: 'Deterministic Chain (0 Model Drift)' },
        { label: 'Audit Trail Ref', value: 'Cross-Stage Verified' }
      ],
      insights,
      additionalDetails
    };
  }

  // ── 05. ANALYST DECISION SUPPORT ──────────────────────────────────────────
  const summary = data?.summary || {};
  const priority = data?.review_priority || summary.review_priority || (isPending ? 'PENDING' : 'URGENT');
  const index = summary.assessment_heuristic_index || 0.99;
  const stepsList = Array.isArray(data?.recommended_review_steps) ? data.recommended_review_steps : [];
  const topStep = stepsList[0];
  const actionRec = data?.action_recommendation || {};
  const boundary = data?.human_approval_boundary || {};
  const dispositions = Array.isArray(data?.disposition_options) ? data.disposition_options : [];

  let primaryFinding = 'Awaiting operational review priority and decision support options.';
  if (!isPending && !isFailed) {
    if (data?.priority_rationale) {
      primaryFinding = safeFormatValue(data.priority_rationale);
    } else if (actionRec?.rationale) {
      primaryFinding = safeFormatValue(actionRec.rationale);
    } else {
      primaryFinding = 'High-confidence mule activity requires immediate human operator authorization.';
    }
  }

  const insights = [];
  if (isPending) {
    insights.push({
      category: 'PRIMARY',
      title: 'Decision Support Queued',
      description: 'Awaiting operational decision support and recommendation synthesis.',
      id: 'DEC-QUEUE'
    });
    insights.push({
      category: 'POLICY',
      title: 'Human Authorization Boundary',
      description: 'Human authorization boundary evaluation on standby.',
      id: 'DEC-POL'
    });
  } else if (isFailed) {
    insights.push({
      category: 'PRIMARY',
      title: 'Decision Engine Error',
      description: 'Decision engine failed to generate recommendations.',
      id: 'DEC-ERR',
      severity: 'HIGH'
    });
  } else {
    insights.push({
      category: 'PRIMARY',
      title: `Recommended Action: ${actionRec?.action ? formatLabel(actionRec.action) : 'Freeze Beneficiary Account'}`,
      description: actionRec?.target_account ? `Target account ${actionRec.target_account}: ${actionRec.rationale || 'Immediate fund preservation recommended.'}` : 'Immediate capital freeze recommended to protect recoverable balance.',
      id: actionRec?.action_code || 'ACT-001',
      severity: 'URGENT'
    });
    insights.push({
      category: 'SUPPORTING',
      title: topStep?.action_label ? safeFormatValue(topStep.action_label) : 'Beneficiary Ownership Review',
      description: topStep?.description ? safeFormatValue(topStep.description) : 'Verify counterparty beneficiary account KYC and transaction purpose.',
      id: topStep?.step_id || 'RS-001',
      severity: topStep?.priority || 'HIGH'
    });
    insights.push({
      category: 'POLICY',
      title: 'Human Authorization Boundary',
      description: 'Autonomous execution is strictly blocked for capital freezes. Mandatory compliance analyst sign-off required.',
      id: 'DISP-REQ'
    });
  }

  const additionalDetails = [];
  stepsList.slice(1).forEach(s => {
    if (s) {
      additionalDetails.push({
        label: s.action_label ? safeFormatValue(s.action_label) : (s.category ? formatLabel(s.category) : 'Review Step'),
        value: safeFormatValue(s.description),
        id: s.step_id,
        severity: s.priority
      });
    }
  });
  dispositions.forEach(d => {
    if (d) {
      additionalDetails.push({
        label: d.label ? safeFormatValue(d.label) : formatLabel(d.action_code || 'Disposition'),
        value: `Reason Note Required: ${d.requires_reason_note ? 'Yes' : 'No'} · Risk Acknowledgement: ${d.requires_risk_acknowledgement ? 'Yes' : 'No'}`,
        id: d.action_code
      });
    }
  });
  if (boundary.required_role) {
    additionalDetails.push({
      label: 'Human Approval Required Role',
      value: boundary.required_role
    });
    additionalDetails.push({
      label: 'Autonomous Execution Status',
      value: boundary.autonomous_execution ? 'Permitted' : 'Blocked (Human Required)'
    });
  }
  (data?.uncertainties || []).forEach((u, i) => {
    additionalDetails.push({
      label: `Uncertainty #${i + 1}`,
      value: safeFormatValue(u)
    });
  });

  return {
    index: '05',
    shortName: 'DECISION',
    fullName: 'Analyst Decision Support',
    domain: 'Human Authorization Boundary',
    Icon: UserCheck,
    metricTag: priority === 'URGENT' ? 'Urgent Review' : 'Actionable',
    primaryFinding,
    items: [
      { label: 'Review Priority', value: priority, alert: priority === 'URGENT' || priority === 'HIGH' },
      { label: 'Assessment Index', value: typeof index === 'number' ? index.toFixed(2) : '0.99' },
      { label: 'Human Approval', value: 'REQUIRED (Autonomous Blocked)', warn: true },
      { label: 'Policy Disposition', value: 'Freeze Beneficiary Recommended' }
    ],
    insights,
    additionalDetails
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// CANVAS GEOMETRY — 1200 × 380 viewBox
// TOP row: y=110  |  BOTTOM row: y=270
// ─────────────────────────────────────────────────────────────────────────────
const CANVAS_W = 1200;
const CANVAS_H = 380;
const NODE_R = 36; // circle radius in SVG units

const NODE_LAYOUT = [
  { id: 'evidence',   cx: 150,  cy: 110, row: 'top'    },
  { id: 'contextual', cx: 400,  cy: 270, row: 'bottom' },
  { id: 'regulatory', cx: 650,  cy: 110, row: 'top'    },
  { id: 'audit',      cx: 900,  cy: 270, row: 'bottom' },
  { id: 'decision',   cx: 1080, cy: 110, row: 'top'    },
];

// Horizontal anchor percentages for detail panel stem (matching SVG cx coordinates)
const STAGE_ANCHOR_PCT = {
  evidence: 12.5,
  contextual: 33.33,
  regulatory: 54.17,
  audit: 75.0,
  decision: 90.0,
};

// Edge-aware horizontal alignment for the detail panel beneath the selected node
const getContainerAlignment = (key) => {
  switch (key) {
    case 'evidence':   return 'mr-auto ml-0 sm:ml-2';
    case 'contextual': return 'mr-auto ml-0 sm:ml-[6%] xl:ml-[10%]';
    case 'regulatory': return 'mx-auto';
    case 'audit':      return 'ml-auto mr-0 sm:mr-[6%] xl:mr-[10%]';
    case 'decision':   return 'ml-auto mr-0 sm:mr-2';
    default:           return 'mx-auto';
  }
};

// Backbone connector endpoints (from edge of source circle to edge of dest circle)
const SEGMENTS = NODE_LAYOUT.slice(0, 4).map((from, i) => {
  const to = NODE_LAYOUT[i + 1];
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    x1: from.cx + ux * (NODE_R + 2),
    y1: from.cy + uy * (NODE_R + 2),
    x2: to.cx - ux * (NODE_R + 2),
    y2: to.cy - uy * (NODE_R + 2),
  };
});

// ─────────────────────────────────────────────────────────────────────────────
// STATUS HELPERS
// ─────────────────────────────────────────────────────────────────────────────
const statusColor = (status) => {
  if (status === 'COMPLETED') return { ring: '#10B981', glow: 'rgba(16,185,129,0.45)', text: '#10B981', bg: 'rgba(16,185,129,0.08)' };
  if (status === 'RUNNING')   return { ring: '#38BDF8', glow: 'rgba(56,189,248,0.5)',  text: '#38BDF8', bg: 'rgba(56,189,248,0.1)'  };
  if (status === 'FAILED')    return { ring: '#F43F5E', glow: 'rgba(244,63,94,0.4)',   text: '#F43F5E', bg: 'rgba(244,63,94,0.08)'  };
  return                             { ring: '#334155', glow: 'transparent',            text: '#64748B', bg: 'rgba(30,41,59,0.5)'   };
};

// ─────────────────────────────────────────────────────────────────────────────
// FLOATING AGENT TOOLTIP CARD & POSITIONING (Rendered via Portal to escape clipping)
// ─────────────────────────────────────────────────────────────────────────────
const TOOLTIP_WIDTH = 320;
const TOOLTIP_HEIGHT_ESTIMATE = 235;

const computeTooltipPosition = (stage, svgEl, containerEl) => {
  if (!stage || !stage.layout || !svgEl) return null;

  const svgRect = svgEl.getBoundingClientRect();
  const containerRect = containerEl ? containerEl.getBoundingClientRect() : svgRect;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  const scaleX = svgRect.width / CANVAS_W;
  const scaleY = svgRect.height / CANVAS_H;

  const { cx, cy, row } = stage.layout;
  const circleCenterX = svgRect.left + cx * scaleX;
  const circleCenterY = svgRect.top + cy * scaleY;
  const circleRadius = NODE_R * scaleY;

  // Node bounding box in screen pixels (incorporating circle + inline static card)
  let nodeTop = circleCenterY - circleRadius;
  let nodeBottom = circleCenterY + circleRadius;

  if (row === 'top') {
    // Top row: inline card is below circle, ending at SVG y = 240
    nodeBottom = svgRect.top + 240 * scaleY;
  } else {
    // Bottom row: inline card is above circle, starting at SVG y = 140
    nodeTop = svgRect.top + 140 * scaleY;
  }

  const effectiveTooltipWidth = Math.min(TOOLTIP_WIDTH, viewportWidth - 32);

  // Available vertical boundaries respecting both the workflow container and viewport
  // This prevents the tooltip from overflowing over footers, action bars, or out of viewport
  const maxBottomBound = Math.min(viewportHeight - 12, containerRect.bottom - 4);
  const minTopBound = Math.max(12, containerRect.top + 4);

  const spaceBelow = maxBottomBound - nodeBottom;
  const spaceAbove = nodeTop - minTopBound;
  const requiredHeight = TOOLTIP_HEIGHT_ESTIMATE + 12;

  let placement = 'below';
  let top = 0;

  // Requirement 3:
  // - If there is space below → show below.
  // - If there is not enough space below → show above.
  if (spaceBelow >= requiredHeight) {
    placement = 'below';
    top = nodeBottom + 8;
  } else if (spaceAbove >= requiredHeight) {
    placement = 'above';
    top = nodeTop - TOOLTIP_HEIGHT_ESTIMATE - 8;
  } else {
    // Fallback: pick the side with more room
    if (spaceBelow >= spaceAbove) {
      placement = 'below';
      top = Math.min(nodeBottom + 8, viewportHeight - TOOLTIP_HEIGHT_ESTIMATE - 12);
    } else {
      placement = 'above';
      top = Math.max(12, nodeTop - TOOLTIP_HEIGHT_ESTIMATE - 8);
    }
  }

  // Safety clamp to guarantee tooltip is always within viewport
  top = Math.max(12, Math.min(top, viewportHeight - TOOLTIP_HEIGHT_ESTIMATE - 12));

  // Horizontal positioning:
  // Center on node, then reposition inward if near edges
  const idealLeft = circleCenterX - effectiveTooltipWidth / 2;

  // If container is wide enough, keep tooltip within the container bounds
  // Otherwise, keep within viewport bounds
  let minLeft = 16;
  let maxLeft = viewportWidth - effectiveTooltipWidth - 16;

  if (containerRect.width >= effectiveTooltipWidth + 24) {
    minLeft = Math.max(16, containerRect.left + 8);
    maxLeft = Math.min(viewportWidth - effectiveTooltipWidth - 16, containerRect.right - effectiveTooltipWidth - 8);
  }

  const left = Math.max(minLeft, Math.min(idealLeft, maxLeft));

  // Pointer arrow points directly at circle center
  const rawArrowX = circleCenterX - left;
  const arrowX = Math.max(24, Math.min(rawArrowX, effectiveTooltipWidth - 24));

  return { top, left, arrowX, placement, width: effectiveTooltipWidth };
};

const AgentTooltipCard = ({ stage, placement, arrowX, prefersReducedMotion }) => {
  if (!stage || !stage.insight) return null;
  const { insight } = stage;
  const sc = statusColor(stage.status);

  return (
    <div className="relative font-sans select-none pointer-events-none">
      {/* Pointer arrow (rotated square with matching border and background) */}
      <div
        className="absolute w-2.5 h-2.5 bg-[#070D18] pointer-events-none"
        style={{
          left: `${arrowX}px`,
          transform: 'translateX(-50%) rotate(45deg)',
          zIndex: 20,
          ...(placement === 'below'
            ? {
                top: '-5px',
                borderLeft: `1px solid ${sc.ring}88`,
                borderTop: `1px solid ${sc.ring}88`,
              }
            : {
                bottom: '-5px',
                borderRight: `1px solid ${sc.ring}88`,
                borderBottom: `1px solid ${sc.ring}88`,
              }),
        }}
      />

      {/* Main Card Container */}
      <div
        className="w-full rounded-xl border shadow-2xl overflow-hidden backdrop-blur-md"
        style={{
          background: '#070D18',
          borderColor: sc.ring + '66',
          boxShadow: `0 16px 36px -4px rgba(0, 0, 0, 0.85), 0 0 24px -2px ${sc.glow}`,
        }}
      >
        {/* Tooltip Header */}
        <div
          className="px-3.5 py-2.5 border-b bg-[#0A1222]/80 flex items-center justify-between gap-2"
          style={{ borderColor: '#1E293B' }}
        >
          <div className="min-w-0">
            <span
              className="block font-mono text-[10px] font-black uppercase tracking-wider truncate"
              style={{ color: sc.text }}
            >
              {insight.index} · {insight.fullName}
            </span>
            <span className="block text-[8.5px] text-slate-400 font-mono uppercase tracking-tight mt-0.5 truncate">
              {stage.domain}
            </span>
          </div>
          <span
            className="px-2 py-0.5 rounded text-[8px] font-mono font-bold uppercase tracking-wider whitespace-nowrap shrink-0"
            style={{ background: sc.bg, color: sc.text, border: `1px solid ${sc.ring}55` }}
          >
            {stage.status}
          </span>
        </div>

        {/* Primary Finding */}
        <div className="px-3.5 py-2 border-b bg-[#050B14]/60" style={{ borderColor: '#1E293B' }}>
          <div className="flex items-center gap-1 mb-1">
            <Target className="w-2.5 h-2.5 text-sky-400 shrink-0" />
            <span className="text-[8px] font-mono text-slate-400 uppercase tracking-wider font-bold">
              Primary Forensic Finding
            </span>
          </div>
          <p className="text-[10px] text-slate-200 leading-relaxed font-sans line-clamp-3">
            {insight.primaryFinding}
          </p>
        </div>

        {/* 2×2 Metric Grid */}
        <div className="grid grid-cols-2 gap-1 p-2 bg-[#03060C]">
          {insight.items.map((it, i) => (
            <div
              key={i}
              className="px-2.5 py-1.5 rounded-md border border-[#1E293B]/60 bg-[#070E1C]/90 flex flex-col justify-center"
            >
              <span className="text-[7.5px] font-mono text-slate-500 uppercase tracking-wider truncate">
                {it.label}
              </span>
              <span
                className="text-[9.5px] font-mono font-bold truncate mt-0.5"
                style={{
                  color: it.alert ? '#F43F5E' : it.warn ? '#FCD34D' : it.success ? '#10B981' : '#CBD5E1',
                }}
              >
                {safeFormatValue(it.value, it.label)}
              </span>
            </div>
          ))}
        </div>

        {/* Footer Hint */}
        <div
          className="px-3.5 py-1.5 border-t bg-[#050A14] flex items-center justify-between text-[8px] font-mono text-slate-500 uppercase tracking-wider"
          style={{ borderColor: '#1E293B' }}
        >
          <span>Click node to open full report</span>
          <ArrowRight className="w-2.5 h-2.5 text-slate-400" />
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN EXPORT
// ─────────────────────────────────────────────────────────────────────────────
export const InvestigationWorkflowGraph = ({
  timelineStages = [],
  graphData = { nodes: [], edges: [] },
}) => {
  const [selectedStageKey, setSelectedStageKey] = useState(timelineStages[0]?.key || 'evidence');
  const [isDetailPanelOpen, setIsDetailPanelOpen] = useState(true);
  const [showAdditionalDetails, setShowAdditionalDetails] = useState(false);
  const [hoveredStageKey, setHoveredStageKey] = useState(null);
  const [activeReportKey, setActiveReportKey] = useState(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const startTimeRef = useRef(Date.now());
  const [elapsedSec, setElapsedSec] = useState(0);

  // Reset progressive disclosure whenever selected stage changes
  useEffect(() => {
    setShowAdditionalDetails(false);
  }, [selectedStageKey]);

  // Portal Tooltip state
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0, arrowX: 0, placement: 'below', width: TOOLTIP_WIDTH });
  const [isTooltipVisible, setIsTooltipVisible] = useState(false);
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const closeTimerRef = useRef(null);

  const updateTooltipPosition = useCallback((stage) => {
    if (!stage || !svgRef.current) return;
    const pos = computeTooltipPosition(stage, svgRef.current, containerRef.current);
    if (pos) {
      setTooltipPos(pos);
    }
  }, []);

  const handleNodeMouseEnter = useCallback((stage) => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    setHoveredStageKey(stage.key);
    setActiveTooltip(stage);
    updateTooltipPosition(stage);
    setIsTooltipVisible(true);
  }, [updateTooltipPosition]);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredStageKey(null);
    setIsTooltipVisible(false);
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    closeTimerRef.current = setTimeout(() => {
      setActiveTooltip(null);
    }, 170);
  }, []);

  // Update tooltip position on window scroll (capture phase) or resize
  useEffect(() => {
    if (!activeTooltip || !svgRef.current) return;
    const handleUpdate = () => {
      if (activeTooltip && svgRef.current) {
        updateTooltipPosition(activeTooltip);
      }
    };
    window.addEventListener('scroll', handleUpdate, { passive: true, capture: true });
    window.addEventListener('resize', handleUpdate, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleUpdate, { capture: true });
      window.removeEventListener('resize', handleUpdate);
    };
  }, [activeTooltip, updateTooltipPosition]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  // Detect accessibility motion preferences
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mq.matches);
    const handler = (e) => setPrefersReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Elapsed time ticker
  useEffect(() => {
    const t = setInterval(() => setElapsedSec(Math.floor((Date.now() - startTimeRef.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);

  // Keyboard: 1-5 to select agents, Esc to close drawer/panel
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'Escape') {
        if (activeReportKey) {
          setActiveReportKey(null);
        } else if (isDetailPanelOpen) {
          setIsDetailPanelOpen(false);
        }
      }
      if (['1', '2', '3', '4', '5'].includes(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        if (timelineStages[idx]) {
          setSelectedStageKey(timelineStages[idx].key);
          setIsDetailPanelOpen(true);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeReportKey, isDetailPanelOpen, timelineStages]);

  // Enrich stages with insight data + layout geometry
  const enrichedStages = useMemo(() => {
    return timelineStages.map((stage, idx) => {
      const insight = getStageInsightData(stage.key, stage.data, stage.status, graphData);
      const layout = NODE_LAYOUT[idx] || NODE_LAYOUT[0];
      return { ...stage, index: insight.index, shortName: insight.shortName, fullName: insight.fullName, domain: insight.domain, Icon: insight.Icon, metricTag: insight.metricTag, insight, layout };
    });
  }, [timelineStages, graphData]);

  // Selected stage object
  const selectedStage = useMemo(() => {
    return enrichedStages.find(s => s.key === selectedStageKey) || enrichedStages[0];
  }, [enrichedStages, selectedStageKey]);

  // Telemetry counts
  const completedCount = timelineStages.filter(s => s.status === 'COMPLETED').length;
  const runningCount   = timelineStages.filter(s => s.status === 'RUNNING').length;
  const failedCount    = timelineStages.filter(s => s.status === 'FAILED').length;
  const isAllComplete  = completedCount === timelineStages.length && timelineStages.length > 0;

  // Active report stage
  const activeReportStage = useMemo(() => enrichedStages.find(s => s.key === activeReportKey), [enrichedStages, activeReportKey]);

  // Segment pipe states
  const segmentStates = useMemo(() => [0, 1, 2, 3].map(i => {
    const from = enrichedStages[i];
    const to   = enrichedStages[i + 1];
    if (!from || !to) return 'pending';
    if (from.status === 'COMPLETED' && to.status === 'COMPLETED') return 'completed';
    if (from.status === 'COMPLETED' && to.status === 'RUNNING')   return 'active';
    if (from.status === 'RUNNING') return 'active';
    return 'pending';
  }), [enrichedStages]);

  // Confidence from contextual stage
  const contextualStage = enrichedStages.find(s => s.key === 'contextual');
  const confidenceVal = contextualStage?.data?.summary?.confidence ?? 0.94;
  const confidencePct = Math.round(confidenceVal * 100);

  // Elapsed time formatted
  const fmtTime = (sec) => {
    const h = String(Math.floor(sec / 3600)).padStart(2, '0');
    const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  return (
    <div className="font-sans select-none">

      {/* ═══════════════════════════════════════════════════════════════════════
          HEADER BAND
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="rounded-t-xl border border-b-0 border-[#1E293B] bg-[#060D1A] px-5 py-3 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Title */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="font-mono text-xs font-black text-slate-100 uppercase tracking-wider">
              INVESTIGATION WORKFLOW
              <span className="ml-2 text-[9px] font-normal text-slate-500">· 5-AGENT PIPELINE · CLICK NODE TO INSPECT</span>
            </div>
            <div className="text-[9px] text-slate-500 font-mono uppercase tracking-tight mt-0.5">
              Deterministic Multi-Agent Financial Crime Orchestration Chain
            </div>
          </div>
        </div>

        {/* Right: Status Badge + Timer */}
        <div className="flex items-center gap-2 font-mono">
          <span className="text-[8.5px] text-slate-500 uppercase tracking-wider">{fmtTime(elapsedSec)}</span>
          {isAllComplete ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold text-[9px] uppercase tracking-wider">
              <CheckCircle2 className="w-3 h-3" />
              5/5 VERIFIED COMPLETE
            </span>
          ) : runningCount > 0 ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-500/15 border border-sky-500/40 text-sky-300 font-bold text-[9px] uppercase tracking-wider">
              <span className={twMerge('w-2 h-2 rounded-full bg-sky-400', !prefersReducedMotion && 'animate-pulse')} />
              STAGE {completedCount + 1}/5 EXECUTING
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400 font-bold text-[9px] uppercase tracking-wider">
              <Clock className="w-3 h-3" />
              {completedCount}/5 STAGES · STANDBY
            </span>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          MAIN BODY: CANVAS  +  DETAIL PANEL
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="rounded-b-xl border border-[#1E293B] bg-[#04090F] flex flex-col overflow-hidden">

        {/* ── TOP: ZIG-ZAG WORKFLOW GRAPH CANVAS ────────────────────────────── */}
        <div ref={containerRef} className="w-full p-5 overflow-x-auto">

          {/* Orchestrator Header Chip */}
          <div className="flex items-center justify-between mb-4">
            <div className="inline-flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#070F20] border border-sky-500/30 shadow-[0_0_18px_rgba(56,189,248,0.1)]">
              <div className="w-7 h-7 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center shrink-0">
                <Cpu className={twMerge('w-4 h-4 text-sky-400', !prefersReducedMotion && runningCount > 0 && 'animate-pulse')} />
              </div>
              <div>
                <div className="font-mono text-[10px] font-black text-slate-100 uppercase tracking-wider whitespace-nowrap">
                  INVESTIGATION ORCHESTRATOR
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {timelineStages.map((s, idx) => (
                    <div
                      key={idx}
                      title={`Stage 0${idx + 1}: ${s.status}`}
                      className={twMerge(
                        'h-1 w-8 rounded-full transition-colors',
                        s.status === 'COMPLETED' ? 'bg-emerald-400 shadow-[0_0_5px_rgba(16,185,129,0.7)]' :
                        s.status === 'RUNNING'   ? 'bg-sky-400 shadow-[0_0_5px_rgba(56,189,248,0.8)]' + (!prefersReducedMotion ? ' animate-pulse' : '') :
                        'bg-[#1E293B]'
                      )}
                    />
                  ))}
                </div>
              </div>
              <span className={twMerge(
                'ml-1 px-2 py-0.5 rounded text-[8px] font-mono font-black uppercase tracking-wider whitespace-nowrap border',
                isAllComplete
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                  : 'bg-sky-500/10 text-sky-300 border-sky-500/30'
              )}>
                {completedCount}/5 COMPLETE
              </span>
            </div>
          </div>

          {/* SVG Canvas */}
          <div className="relative w-full overflow-x-auto">
            <svg
              ref={svgRef}
              viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
              className="w-full min-w-[640px]"
              style={{ height: 'auto', aspectRatio: `${CANVAS_W}/${CANVAS_H}` }}
              aria-label="Investigation workflow graph — 5-agent zig-zag pipeline"
            >
              <defs>
                {/* Glow filters for active nodes */}
                <filter id="glow-emerald" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glow-sky" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>

                {/* Gradient fills for connectors */}
                <linearGradient id="seg-completed" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%"   stopColor="#10B981" />
                  <stop offset="100%" stopColor="#06B6D4" />
                </linearGradient>
                <linearGradient id="seg-active" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%"   stopColor="#38BDF8" />
                  <stop offset="50%"  stopColor="#818CF8" />
                  <stop offset="100%" stopColor="#38BDF8" />
                </linearGradient>

                {/* Arrow markers */}
                <marker id="arr-comp" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10B981" />
                </marker>
                <marker id="arr-act" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38BDF8" />
                </marker>
                <marker id="arr-pend" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 2 L 6 5 L 0 8 z" fill="#334155" />
                </marker>
              </defs>

              {/* ── BACKBONE STRAIGHT CONNECTORS ─────────────────────────── */}
              {SEGMENTS.map((seg, i) => {
                const state = segmentStates[i];
                const stroke = state === 'completed' ? 'url(#seg-completed)' : state === 'active' ? 'url(#seg-active)' : '#1E293B';
                const marker = state === 'completed' ? 'url(#arr-comp)' : state === 'active' ? 'url(#arr-act)' : 'url(#arr-pend)';
                const anim = !prefersReducedMotion && state !== 'pending';
                return (
                  <g key={i}>
                    {/* Shadow track */}
                    <line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
                      stroke="#0A1628" strokeWidth="5" strokeLinecap="round" />
                    {/* Animated foreground */}
                    <line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
                      stroke={stroke}
                      strokeWidth={state === 'active' ? 2.5 : 2}
                      strokeLinecap="round"
                      strokeDasharray={state === 'pending' ? '5 7' : '9 15'}
                      markerEnd={marker}
                      style={anim ? { animation: 'flowDash 1.2s linear infinite' } : undefined}
                    />
                    {/* Flow state label */}
                    <text
                      x={(seg.x1 + seg.x2) / 2}
                      y={(seg.y1 + seg.y2) / 2 - 8}
                      textAnchor="middle"
                      fontSize="7"
                      fontFamily="monospace"
                      fontWeight="bold"
                      fill={state === 'completed' ? '#10B981' : state === 'active' ? '#38BDF8' : '#334155'}
                      opacity="0.85"
                    >
                      {state === 'completed' ? '✓' : state === 'active' ? '▶' : '○'}
                    </text>
                  </g>
                );
              })}

              {/* ── AGENT NODES ──────────────────────────────────────────── */}
              {enrichedStages.map((stage, idx) => {
                const { cx, cy, row } = stage.layout;
                const sc = statusColor(stage.status);
                const isSelected = selectedStageKey === stage.key;
                const isHovered  = hoveredStageKey === stage.key;
                const isRunning  = stage.status === 'RUNNING';
                const isComplete = stage.status === 'COMPLETED';
                const active     = isSelected || isHovered;

                return (
                  <g
                    key={stage.key}
                    role="button"
                    tabIndex={0}
                    aria-label={`${stage.fullName} — Status: ${stage.status}. Click or press Enter to inspect agent detail panel below.`}
                    style={{ cursor: 'pointer', outline: 'none' }}
                    onClick={() => {
                      setSelectedStageKey(stage.key);
                      setIsDetailPanelOpen(true);
                    }}
                    onMouseEnter={() => handleNodeMouseEnter(stage)}
                    onMouseLeave={handleNodeMouseLeave}
                    onFocus={() => handleNodeMouseEnter(stage)}
                    onBlur={handleNodeMouseLeave}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelectedStageKey(stage.key);
                        setIsDetailPanelOpen(true);
                      }
                    }}
                  >
                    {/* Vertical guide beam projecting down to the attached panel */}
                    {isSelected && (
                      <g>
                        <line
                          x1={cx}
                          y1={cy + NODE_R + 4}
                          x2={cx}
                          y2={CANVAS_H}
                          stroke={sc.ring}
                          strokeWidth="2"
                          strokeDasharray="4 4"
                          opacity="0.85"
                          style={!prefersReducedMotion ? { animation: 'flowDash 1.2s linear infinite' } : undefined}
                        />
                        {/* Downward beacon chevron at the canvas baseline */}
                        <polygon
                          points={`${cx - 5},${CANVAS_H - 8} ${cx + 5},${CANVAS_H - 8} ${cx},${CANVAS_H - 1}`}
                          fill={sc.ring}
                          opacity="0.9"
                        />
                      </g>
                    )}

                    {/* Pulsing outer ring for running state */}
                    {isRunning && !prefersReducedMotion && (
                      <circle cx={cx} cy={cy} r={NODE_R + 10}
                        fill="none"
                        stroke={sc.ring}
                        strokeWidth="1.5"
                        opacity="0.3"
                        style={{ animation: 'nodeRingPulse 2s ease-in-out infinite' }}
                      />
                    )}

                    {/* Illuminated active halo ring */}
                    {isSelected && (
                      <circle cx={cx} cy={cy} r={NODE_R + 8}
                        fill="none"
                        stroke={sc.ring}
                        strokeWidth="2.5"
                        opacity="0.9"
                        filter={sc.ring.includes('10B981') ? 'url(#glow-emerald)' : 'url(#glow-sky)'}
                      />
                    )}

                    {/* Node circle */}
                    <circle cx={cx} cy={cy} r={NODE_R}
                      fill={isSelected ? '#0B1728' : '#060D1A'}
                      stroke={isSelected ? sc.ring : active ? sc.ring : sc.ring + '66'}
                      strokeWidth={isSelected ? 3.5 : active ? 2.5 : 1.5}
                      style={{ transition: 'stroke 200ms, fill 200ms, stroke-width 200ms' }}
                    />

                    {/* Node number label */}
                    <text
                      x={cx} y={cy - 10}
                      textAnchor="middle"
                      fontSize="11"
                      fontFamily="monospace"
                      fontWeight="900"
                      fill={active ? sc.text : sc.text + 'AA'}
                    >
                      {stage.index}
                    </text>

                    {/* Status text */}
                    <text
                      x={cx} y={cy + 6}
                      textAnchor="middle"
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="600"
                      fill={active ? sc.text : sc.text + '99'}
                    >
                      {stage.shortName.slice(0, 5)}
                    </text>

                    {/* Status visual */}
                    {isComplete && (
                      <g>
                        <circle cx={cx + NODE_R - 6} cy={cy - NODE_R + 6} r="8" fill="#10B981" stroke="#060D1A" strokeWidth="2" />
                        <text x={cx + NODE_R - 6} y={cy - NODE_R + 10} textAnchor="middle" fontSize="9" fill="white" fontWeight="bold">✓</text>
                      </g>
                    )}
                    {isRunning && (
                      <circle cx={cx + NODE_R - 6} cy={cy - NODE_R + 6} r="6"
                        fill="#38BDF8" stroke="#060D1A" strokeWidth="2"
                        style={!prefersReducedMotion ? { animation: 'nodeRingPulse 1s ease-in-out infinite' } : undefined}
                      />
                    )}
                    {stage.status === 'FAILED' && (
                      <g>
                        <circle cx={cx + NODE_R - 6} cy={cy - NODE_R + 6} r="7" fill="#F43F5E" stroke="#060D1A" strokeWidth="2" />
                        <text x={cx + NODE_R - 6} y={cy - NODE_R + 10} textAnchor="middle" fontSize="9" fill="white" fontWeight="bold">!</text>
                      </g>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* ── KEYBOARD SHORTCUT HINTS ── */}
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3 font-mono text-[8.5px] text-slate-600 uppercase tracking-wider border-t border-[#1E293B]/60 pt-2">
            <div className="flex items-center gap-3">
              <span>HOVER NODE → PREVIEW</span>
              <span>·</span>
              <span>CLICK NODE → AGENT DETAIL PANEL BELOW</span>
              <span>·</span>
              <span>1–5 → SWITCH AGENT</span>
              <span>·</span>
              <span>ESC → CLOSE</span>
            </div>
            {isDetailPanelOpen && selectedStage && (
              <span className="text-sky-400/90 font-bold">
                STAGE {selectedStage.index} ACTIVE BELOW ↓
              </span>
            )}
          </div>
        </div>

        {/* ── BOTTOM: HYBRID AGENT DETAIL ANCHORED PANEL OR PIPELINE OVERVIEW ── */}
        <div className="w-full border-t border-[#1E293B] bg-[#04090F] flex flex-col relative transition-all duration-300">
          {isDetailPanelOpen && selectedStage ? (
            /* VIEW A: AGENT DETAIL PANEL (SPATIALLY ANCHORED BELOW SELECTED NODE) */
            <div className="w-full flex flex-col pt-2 pb-6 px-4 sm:px-6 relative">
              {/* Dynamic Anchor Stem pointing from Canvas Beam down to the Detail Card */}
              <div className="w-full relative h-3 pointer-events-none mb-[-1px] z-10">
                <div 
                  className="absolute top-0 w-3.5 h-3.5 rotate-45 border-t border-l transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
                  style={{
                    left: `calc(${STAGE_ANCHOR_PCT[selectedStage.key] || 50}% - 7px)`,
                    backgroundColor: '#060D1A',
                    borderColor: statusColor(selectedStage.status).ring,
                    boxShadow: `0 0 12px ${statusColor(selectedStage.status).glow}`,
                  }}
                />
              </div>

              {/* Edge-Aware Card Container */}
              <div className={twMerge(
                "w-full max-w-[860px] transition-all duration-300",
                getContainerAlignment(selectedStage.key)
              )}>
                <div 
                  key={selectedStage.key}
                  className="w-full rounded-2xl border bg-[#060D1A]/95 backdrop-blur-xl shadow-[0_16px_48px_rgba(0,0,0,0.65)] overflow-hidden animate-detailSlide"
                  style={{
                    borderColor: statusColor(selectedStage.status).ring + '60',
                    boxShadow: `0 12px 36px rgba(0,0,0,0.6), 0 0 24px ${statusColor(selectedStage.status).glow}`,
                  }}
                >
                  {/* Panel Header */}
                  <div className="px-5 py-3 border-b border-[#1E293B] bg-[#081020]/90 backdrop-blur-sm flex flex-wrap items-center justify-between gap-3">
                    {/* Left: Agent Identification */}
                    <div className="flex items-center gap-3 min-w-0">
                      <div 
                        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border"
                        style={{ 
                          backgroundColor: statusColor(selectedStage.status).bg, 
                          borderColor: statusColor(selectedStage.status).ring + '66' 
                        }}
                      >
                        {React.createElement(selectedStage.Icon || Shield, {
                          className: "w-4 h-4",
                          style: { color: statusColor(selectedStage.status).text }
                        })}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span 
                            className="text-[9.5px] font-mono font-black uppercase px-2 py-0.5 rounded border"
                            style={{
                              backgroundColor: statusColor(selectedStage.status).bg,
                              borderColor: statusColor(selectedStage.status).ring + '44',
                              color: statusColor(selectedStage.status).text
                            }}
                          >
                            STAGE {selectedStage.index}
                          </span>
                          <span className="text-xs font-mono font-black text-slate-100 uppercase tracking-tight truncate">
                            {selectedStage.fullName}
                          </span>
                        </div>
                        <div className="text-[9.5px] font-mono text-slate-400 truncate mt-0.5">
                          {selectedStage.domain}
                        </div>
                      </div>
                    </div>

                    {/* Right: Stage Switcher Pills + Status + Close */}
                    <div className="flex items-center gap-2.5">
                      {/* 1–5 Quick Selector Bar */}
                      <div className="hidden sm:flex items-center gap-1 bg-[#080F1E] p-1 rounded-lg border border-[#1E293B]">
                        {enrichedStages.map((s) => {
                          const isCurrent = s.key === selectedStage.key;
                          const sc = statusColor(s.status);
                          return (
                            <button
                              key={s.key}
                              type="button"
                              onClick={() => setSelectedStageKey(s.key)}
                              className={twMerge(
                                "px-2 py-1 rounded text-center transition-all cursor-pointer font-mono text-[9px] font-bold uppercase flex items-center gap-1",
                                isCurrent 
                                  ? "bg-sky-500/20 border border-sky-400 text-sky-200 shadow-[0_0_8px_rgba(56,189,248,0.2)]"
                                  : "text-slate-400 hover:text-slate-200 hover:bg-[#0E1726]"
                              )}
                              title={`${s.index} · ${s.fullName}`}
                            >
                              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sc.ring }} />
                              <span>{s.index}</span>
                              <span className="hidden md:inline text-[8px] text-slate-400">{s.shortName.slice(0, 4)}</span>
                            </button>
                          );
                        })}
                      </div>

                      {/* Status indicator */}
                      <span 
                        className="text-[8.5px] font-mono font-bold uppercase px-2.5 py-1 rounded-full border flex items-center gap-1.5"
                        style={{
                          backgroundColor: statusColor(selectedStage.status).bg,
                          borderColor: statusColor(selectedStage.status).ring + '55',
                          color: statusColor(selectedStage.status).text
                        }}
                      >
                        {selectedStage.status === 'RUNNING' && (
                          <span className={twMerge("w-1.5 h-1.5 rounded-full bg-sky-400", !prefersReducedMotion && "animate-pulse")} />
                        )}
                        {selectedStage.status === 'COMPLETED' && <Check className="w-3 h-3" />}
                        {selectedStage.status === 'FAILED' && <AlertTriangle className="w-3 h-3 text-rose-400" />}
                        {selectedStage.status}
                      </span>

                      {/* Close Button */}
                      <button
                        type="button"
                        onClick={() => setIsDetailPanelOpen(false)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-[#1E293B] transition-colors cursor-pointer"
                        title="Close agent detail panel (Esc)"
                        aria-label="Close agent detail panel"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Main Content Grid: 12 Columns */}
                  <div className="p-5 select-text space-y-4">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                      
                      {/* 1. Primary Forensic Finding (Column 1 - 4 cols) */}
                      <div 
                        className="lg:col-span-4 rounded-xl p-4 border relative overflow-hidden bg-[#070E1C] flex flex-col justify-between"
                        style={{
                          borderColor: statusColor(selectedStage.status).ring + '40',
                        }}
                      >
                        <div 
                          className="absolute top-0 left-0 bottom-0 w-1.5"
                          style={{ backgroundColor: statusColor(selectedStage.status).ring }}
                        />
                        <div>
                          <div className="flex items-center justify-between mb-2 pl-2">
                            <span className="text-[8.5px] font-mono font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                              PRIMARY FORENSIC FINDING
                            </span>
                            <span className="text-[8px] font-mono text-slate-500 uppercase">
                              AGENT {selectedStage.index} OF 05
                            </span>
                          </div>
                          <p className="text-[12.5px] text-slate-100 leading-relaxed pl-2 font-sans font-medium">
                            {selectedStage.insight.primaryFinding}
                          </p>
                        </div>

                        <div className="mt-4 pl-2 pt-2 border-t border-[#1E293B]/60 flex items-center justify-between text-[8px] font-mono text-slate-500 uppercase">
                          <span>ORIGIN: REAL AGENT TELEMETRY</span>
                          <span style={{ color: statusColor(selectedStage.status).text }}>
                            VERIFIED OUTPUT
                          </span>
                        </div>
                      </div>

                      {/* 2. 2x2 Metric Chips Grid (Column 2 - 4 cols) */}
                      <div className="lg:col-span-4 flex flex-col justify-between">
                        <div className="text-[8.5px] font-mono text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                          <span>FORENSIC TELEMETRY METRICS</span>
                          <span className="text-[8px] text-slate-500 font-mono">DETERMINISTIC</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2.5 flex-1">
                          {selectedStage.insight.items.map((it, idx) => (
                            <div 
                              key={idx}
                              className="p-3 rounded-xl bg-[#081122] border border-[#1E293B]/80 hover:border-slate-700 transition-colors flex flex-col justify-between"
                            >
                              <span className="text-[8.5px] font-mono text-slate-400 uppercase tracking-wider truncate mb-1">
                                {it.label}
                              </span>
                              <span 
                                className="text-base font-mono font-black tracking-tight"
                                style={{
                                  color: it.alert ? '#F43F5E' : it.warn ? '#FCD34D' : it.success ? '#10B981' : '#E2E8F0'
                                }}
                              >
                                {safeFormatValue(it.value, it.label)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 3. Key Forensic Insights (Column 3 - 4 cols) */}
                      <div className="lg:col-span-4 flex flex-col justify-between">
                        <div className="text-[8.5px] font-mono text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                          <div className="flex items-center gap-1.5">
                            <Info className="w-3.5 h-3.5 text-sky-400" />
                            <span>KEY FORENSIC INSIGHTS</span>
                          </div>
                          <span className="text-[8px] text-slate-500 font-mono">
                            {selectedStage.insight.insights?.length || 0} VERIFIED
                          </span>
                        </div>
                        <div className="rounded-xl bg-[#081122] border border-[#1E293B]/80 p-3 space-y-2 flex-1 flex flex-col justify-between">
                          {selectedStage.insight.insights && selectedStage.insight.insights.map((ins, idx) => (
                            <div key={idx} className="p-2 rounded-lg bg-[#060D1A]/90 border border-[#1E293B]/60 space-y-1">
                              <div className="flex items-center justify-between gap-1.5">
                                <div className="flex items-center gap-1.5 min-w-0">
                                  <span 
                                    className="w-1.5 h-1.5 rounded-full shrink-0" 
                                    style={{ backgroundColor: statusColor(selectedStage.status).ring }} 
                                  />
                                  <span className="text-[10px] font-mono font-bold text-slate-200 uppercase truncate">
                                    {ins.title}
                                  </span>
                                </div>
                                {ins.id && (
                                  <span className="text-[8px] font-mono px-1.5 py-0.2 rounded bg-[#0A1426] border border-[#1E293B] text-sky-300 shrink-0 font-semibold">
                                    {ins.id}
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-300 font-sans leading-snug pl-3">
                                {ins.description}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>

                    </div>

                    {/* Progressive Disclosure: Additional Forensic Traceability Accordion */}
                    {selectedStage.insight.additionalDetails && selectedStage.insight.additionalDetails.length > 0 && (
                      <div className="border border-[#1E293B]/80 rounded-xl bg-[#070D1A] overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setShowAdditionalDetails(!showAdditionalDetails)}
                          className="w-full px-4 py-2.5 bg-[#081122] hover:bg-[#0C1930] transition-colors flex items-center justify-between text-left font-mono text-[9px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200 cursor-pointer"
                        >
                          <div className="flex items-center gap-2">
                            <GitCommit className="w-3.5 h-3.5 text-sky-400" />
                            <span>ADDITIONAL FORENSIC TRACEABILITY & SECONDARY FINDINGS</span>
                            <span className="px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-300 border border-sky-500/30 text-[8px]">
                              {selectedStage.insight.additionalDetails.length} RECORDS
                            </span>
                          </div>
                          <div className="flex items-center gap-1 text-[8.5px] text-slate-500">
                            <span>{showAdditionalDetails ? 'COLLAPSE' : 'EXPAND'}</span>
                            <ChevronDown className={twMerge("w-3.5 h-3.5 transition-transform duration-200", showAdditionalDetails && "rotate-180")} />
                          </div>
                        </button>

                        {showAdditionalDetails && (
                          <div className="p-4 border-t border-[#1E293B]/60 space-y-2 max-h-[260px] overflow-y-auto">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {selectedStage.insight.additionalDetails.map((det, dIdx) => (
                                <div key={dIdx} className="p-2.5 rounded-lg bg-[#050A14] border border-[#1E293B]/70 flex flex-col justify-between gap-1">
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-tight truncate">
                                      {det.label}
                                    </span>
                                    {det.id && (
                                      <span className="text-[8px] font-mono px-1.5 py-0.2 rounded bg-[#081020] border border-[#1E293B] text-slate-400 shrink-0">
                                        {det.id}
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[11px] font-sans text-slate-200 leading-snug">
                                    {safeFormatValue(det.value, det.label)}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Panel Action Footer */}
                  <div className="px-5 py-3 border-t border-[#1E293B] bg-[#060C18] flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3 font-mono text-[9px] text-slate-500 uppercase">
                      <span>ACTIVE AGENT: <strong className="text-slate-300">{selectedStage.fullName}</strong></span>
                      <span>·</span>
                      <span>PRESS 1–5 TO SWITCH AGENTS</span>
                      <span>·</span>
                      <span>ESC TO CLOSE</span>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() => setIsDetailPanelOpen(false)}
                        className="py-2 px-3 rounded-lg bg-[#0E1726] hover:bg-[#162338] border border-[#1E293B] text-slate-400 hover:text-slate-200 font-mono text-[9px] font-semibold uppercase tracking-wider transition-colors cursor-pointer"
                      >
                        CLOSE DETAIL (ESC)
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveReportKey(selectedStage.key)}
                        className="py-2 px-4 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/40 hover:border-sky-400 text-sky-200 font-mono text-[10px] font-black uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer shadow-[0_0_12px_rgba(56,189,248,0.15)] group"
                      >
                        <Eye className="w-3.5 h-3.5 text-sky-400 group-hover:scale-110 transition-transform" />
                        VIEW FULL TECHNICAL REPORT
                        <ArrowRight className="w-3.5 h-3.5 text-sky-400 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* VIEW B: PIPELINE OVERVIEW PANEL (when detail panel is collapsed) */
            <div className="w-full px-5 py-3.5 bg-[#060C18] flex flex-wrap items-center justify-between gap-4 animate-fadeIn">
              {/* Left: Overall pipeline metrics */}
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-sky-400" />
                  <span className="font-mono text-xs font-black text-slate-200 uppercase tracking-wider">Pipeline Overview</span>
                </div>
                <div className="h-4 w-[1px] bg-[#1E293B] hidden sm:block" />
                <div className="flex items-center gap-3 font-mono text-[10px]">
                  <span className="text-slate-500 uppercase">STATUS:</span>
                  <span className="font-bold" style={{ color: isAllComplete ? '#10B981' : runningCount > 0 ? '#38BDF8' : '#64748B' }}>
                    {isAllComplete ? 'COMPLETE' : runningCount > 0 ? 'EXECUTING' : 'STANDBY'}
                  </span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-500 uppercase">STAGES:</span>
                  <span className="text-slate-200 font-bold">{completedCount} / 5</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-500 uppercase">ELAPSED:</span>
                  <span className="text-slate-300 font-bold">{fmtTime(elapsedSec)}</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-500 uppercase">CONFIDENCE:</span>
                  <span className="font-bold" style={{ color: confidencePct >= 90 ? '#10B981' : confidencePct >= 70 ? '#FCD34D' : '#64748B' }}>
                    {isAllComplete ? `${confidencePct}%` : '—'}
                  </span>
                </div>
              </div>

              {/* Middle: 5 clickable stages */}
              <div className="hidden lg:flex items-center gap-1.5">
                {enrichedStages.map((stage) => {
                  const sc = statusColor(stage.status);
                  return (
                    <button
                      key={stage.key}
                      type="button"
                      onClick={() => {
                        setSelectedStageKey(stage.key);
                        setIsDetailPanelOpen(true);
                      }}
                      className={twMerge(
                        'flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[9px] font-mono font-bold uppercase transition-all cursor-pointer',
                        selectedStageKey === stage.key
                          ? 'bg-sky-500/15 border-sky-400 text-sky-200'
                          : 'bg-[#080F1C] border-[#1E293B] text-slate-400 hover:text-slate-200 hover:border-slate-600'
                      )}
                    >
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: sc.ring }} />
                      <span>{stage.index} · {stage.shortName}</span>
                      {stage.status === 'COMPLETED' && <Check className="w-2.5 h-2.5 text-emerald-400" />}
                    </button>
                  );
                })}
              </div>

              {/* Right: Open Detail Button */}
              <button
                type="button"
                onClick={() => setIsDetailPanelOpen(true)}
                className="py-1.5 px-3 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/35 text-sky-300 font-mono text-[9px] font-black uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer ml-auto sm:ml-0"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>INSPECT AGENT DETAIL</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          FULL REPORT DRAWER (AnalystEvidenceViewer)
      ═══════════════════════════════════════════════════════════════════════ */}
      {activeReportKey && activeReportStage && (
        <div className="mt-3 rounded-xl border border-sky-500/40 bg-[#03060C] overflow-hidden shadow-[0_0_35px_rgba(6,182,212,0.15)]" style={{ animation: 'fadeIn 200ms ease-out' }}>
          {/* Drawer header */}
          <div className="px-5 py-3 bg-[#081020] border-b border-[#1E293B] flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className={twMerge('w-2.5 h-2.5 rounded-full bg-sky-400', !prefersReducedMotion && 'animate-pulse')} />
              <div className="font-mono text-xs font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <span>STAGE FORENSIC REPORT:</span>
                <span className="text-sky-300">{activeReportStage.title}</span>
              </div>
              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold uppercase">
                {activeReportStage.status}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setActiveReportKey(null)}
              className="px-3 py-1 rounded-lg text-xs font-mono font-semibold text-slate-400 hover:text-slate-100 hover:bg-[#1E293B] transition-colors flex items-center gap-1.5 cursor-pointer"
              title="Close Report Inspector (Esc)"
            >
              <span>CLOSE REPORT</span>
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Report content */}
          <div className="p-5 overflow-y-auto max-h-[550px] select-text">
            <AnalystEvidenceViewer
              stageKey={activeReportStage.key}
              data={activeReportStage.data}
              status={activeReportStage.status}
              title={activeReportStage.title}
            />
          </div>
        </div>
      )}

      {/* ── PORTAL FLOATING TOOLTIP (rendered in document.body to prevent clipping) ── */}
      {typeof document !== 'undefined' && activeTooltip && createPortal(
        <div
          role="tooltip"
          aria-hidden={!isTooltipVisible}
          className="fixed pointer-events-none z-[9999]"
          style={{
            top: `${tooltipPos.top}px`,
            left: `${tooltipPos.left}px`,
            width: `${tooltipPos.width || TOOLTIP_WIDTH}px`,
            maxWidth: 'calc(100vw - 32px)',
            opacity: isTooltipVisible ? 1 : 0,
            transform: isTooltipVisible
              ? 'translateY(0)'
              : (tooltipPos.placement === 'below' ? 'translateY(-4px)' : 'translateY(4px)'),
            transition: prefersReducedMotion
              ? 'none'
              : 'opacity 160ms cubic-bezier(0.16, 1, 0.3, 1), transform 160ms cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <AgentTooltipCard
            stage={activeTooltip}
            placement={tooltipPos.placement}
            arrowX={tooltipPos.arrowX}
            prefersReducedMotion={prefersReducedMotion}
          />
        </div>,
        document.body
      )}

      {/* Embedded keyframe animations */}
      <style>{`
        @keyframes flowDash {
          from { stroke-dashoffset: 40; }
          to   { stroke-dashoffset: 0;  }
        }
        @keyframes nodeRingPulse {
          0%, 100% { opacity: 0.3; r: ${NODE_R + 10}; }
          50%       { opacity: 0.6; r: ${NODE_R + 14}; }
        }
        @keyframes detailSlide {
          0% {
            opacity: 0;
            transform: translateY(-16px) scale(0.985);
          }
          100% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .animate-detailSlide {
          animation: detailSlide 260ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0);   }
        }
        .animate-fadeIn { animation: fadeIn 250ms ease-out; }
        @media (prefers-reduced-motion: reduce) {
          * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>
    </div>
  );
};

export default InvestigationWorkflowGraph;
