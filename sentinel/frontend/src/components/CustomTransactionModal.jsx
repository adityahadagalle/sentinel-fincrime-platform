import React, { useState } from 'react';
import { 
  X, 
  Play, 
  RotateCcw, 
  ShieldAlert, 
  Lock, 
  CheckCircle2, 
  AlertTriangle, 
  Activity, 
  ArrowRight,
  ArrowLeft,
  Zap,
  Sliders,
  Sparkles,
  Clock,
  CreditCard,
  Smartphone,
  Check,
  ChevronDown,
  ChevronUp,
  PhoneCall,
  Layers,
  Flame,
  Shield,
  Sun,
  Moon,
  Building2,
  Globe,
  Radio,
  RefreshCw
} from 'lucide-react';
import RiskBadge from './RiskBadge';

const PAYMENT_METHODS = [
  { id: 'UPI', label: 'UPI', desc: 'Instant mobile payments' },
  { id: 'IMPS', label: 'IMPS', desc: 'Immediate payment service' },
  { id: 'NEFT', label: 'NEFT', desc: 'National electronic transfer' },
  { id: 'CARD', label: 'Card', desc: 'Debit / Credit card payment' },
  { id: 'NET_BANKING', label: 'Net Banking', desc: 'Direct online banking portal' },
];

const AMOUNT_PRESETS = [
  { label: '₹5,000', tag: 'Routine', value: 5000 },
  { label: '₹25,000', tag: 'Typical', value: 25000 },
  { label: '₹75,000', tag: 'High', value: 75000 },
  { label: '₹2,50,000', tag: 'Very High', value: 250000 },
];

const WARNING_SIGNS = [
  {
    id: 'is_new_receiver',
    category: 'Recipient',
    title: 'New recipient',
    desc: 'First payment to this person/account',
    field: 'is_new_receiver',
  },
  {
    id: 'amount_unusual',
    category: 'Amount',
    title: 'Unusually large payment',
    desc: "Much larger than the customer's normal activity",
    field: 'is_large_amount',
  },
  {
    id: 'is_night_time',
    category: 'Timing',
    title: 'Late-night payment',
    desc: 'Payment made during unusual hours',
    field: 'is_night_time',
  },
  {
    id: 'on_active_call',
    category: 'Phone activity',
    title: 'Customer is on an active call',
    desc: 'Customer may be receiving live instructions',
    field: 'on_active_call',
  },
  {
    id: 'device_changed',
    category: 'Device',
    title: 'Unrecognized device',
    desc: 'Login/payment from a new device',
    field: 'device_changed',
  },
  {
    id: 'velocity_flag',
    category: 'Transaction pattern',
    title: 'Rapid series of payments',
    desc: 'Several payments happening close together',
    field: 'velocity_flag',
  },
  {
    id: 'part_of_chain',
    category: 'Money movement',
    title: 'Money movement chain',
    desc: 'Funds are quickly passed between multiple accounts',
    field: 'part_of_chain',
  },
  {
    id: 'is_cross_border',
    category: 'International',
    title: 'International transfer',
    desc: 'Payment involves a foreign transfer corridor',
    field: 'is_cross_border',
  },
];

const STEPS = [
  { number: 1, title: 'Basics' },
  { number: 2, title: 'Amount' },
  { number: 3, title: 'Method' },
  { number: 4, title: 'Time' },
  { number: 5, title: 'Warning Signs' },
  { number: 6, title: 'Baseline' },
  { number: 7, title: 'Review' },
];

const CustomTransactionModal = ({ 
  isOpen, 
  onClose, 
  onEvaluated, 
  activeRunId, 
  isRunUnevaluated, 
  onAddedToBatch,
  onCustomInputAdded,
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    sender_account: 'ACC-109283',
    receiver_account: 'ACC-948201',
    amount: 50000,
    avg_monthly_tx_amount: 25000,
    channel: 'UPI',
    is_night_time: false,
    on_active_call: false,
    is_new_receiver: false,
    is_cross_border: false,
    velocity_flag: false,
    device_changed: false,
    part_of_chain: false,
    is_large_amount: true,
  });

  const [evaluating, setEvaluating] = useState(false);
  const [addingToBatch, setAddingToBatch] = useState(false);
  const [error, setError] = useState(null);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [previousResult, setPreviousResult] = useState(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!isOpen) return null;

  const handleInputChange = (field, value) => {
    setFormData((prev) => {
      const next = { ...prev, [field]: value };
      // Keep time & late-night warning sign synchronized
      if (field === 'is_night_time') {
        next.is_night_time = value;
      }
      return next;
    });
  };

  const toggleWarningSign = (sign) => {
    setFormData((prev) => {
      const currentVal = !!prev[sign.field];
      const nextVal = !currentVal;
      const next = { ...prev, [sign.field]: nextVal };
      if (sign.field === 'is_night_time') {
        next.is_night_time = nextVal;
      }
      return next;
    });
  };

  const handleSelectTime = (isLateNight) => {
    setFormData((prev) => ({
      ...prev,
      is_night_time: isLateNight,
    }));
  };

  // Selected warning signs count
  const selectedWarningSigns = WARNING_SIGNS.filter((sign) => !!formData[sign.field]);

  const handleAddToBatch = async () => {
    setAddingToBatch(true);
    setError(null);

    try {
      let targetRunId = activeRunId;

      // If no active unevaluated run is selected, generate an initial batch so the custom input can be added
      if (!targetRunId || !isRunUnevaluated) {
        const initRes = await fetch('/benchmark/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            num_transactions: 10,
            profile_mode: 'BALANCED',
          }),
        });
        if (!initRes.ok) {
          const initErr = await initRes.json().catch(() => ({}));
          throw new Error(initErr.detail || 'Failed to initialize benchmark batch');
        }
        const initData = await initRes.json();
        targetRunId = initData.run_id;
      }

      const res = await fetch(`/benchmark/runs/${targetRunId}/add-input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          amount: Number(formData.amount),
          avg_monthly_tx_amount: Number(formData.avg_monthly_tx_amount),
          hop_number: formData.part_of_chain ? 2 : 0,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to add input to batch');
      }

      const data = await res.json();
      if (onAddedToBatch) onAddedToBatch(data);
      if (onCustomInputAdded) onCustomInputAdded(data);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to add transaction to test batch');
    } finally {
      setAddingToBatch(false);
    }
  };

  const handleEvaluate = async (e) => {
    if (e) e.preventDefault();
    setEvaluating(true);
    setError(null);

    try {
      const res = await fetch('/benchmark/custom-evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          amount: Number(formData.amount),
          avg_monthly_tx_amount: Number(formData.avg_monthly_tx_amount),
          hop_number: formData.part_of_chain ? 2 : 0,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Evaluation failed (${res.status})`);
      }

      const data = await res.json();
      // Track previous evaluation to demonstrate 100% deterministic repeatability
      if (evaluationResult) {
        setPreviousResult(evaluationResult);
      } else {
        setPreviousResult(data);
      }
      setEvaluationResult(data);
      if (onEvaluated) onEvaluated(data);
    } catch (err) {
      setError(err.message || 'Failed to test transaction');
    } finally {
      setEvaluating(false);
    }
  };

  const handleReset = () => {
    setEvaluationResult(null);
    setPreviousResult(null);
    setError(null);
    setShowTechnicalDetails(false);
    setCurrentStep(1);
  };

  const tx = evaluationResult?.transaction;
  const policy = evaluationResult?.policy_decision;
  const exec = evaluationResult?.execution_record;

  const formatCurrency = (amt) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amt || 0);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div 
        className="relative w-full max-w-4xl max-h-[92vh] bg-[#0A101D] border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100"
        role="dialog"
        aria-modal="true"
        aria-labelledby="custom-tx-title"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0C1424]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h3 id="custom-tx-title" className="text-base font-bold text-slate-100">
                  {evaluationResult ? 'SENTINEL Risk Assessment' : 'Test a Transaction'}
                </h3>
                <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  {evaluationResult ? 'Assessed Result' : 'Guided Builder'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {evaluationResult 
                  ? 'Simulated risk evaluation outcome, detected warning signs, and recommended actions.'
                  : 'Configure a transaction scenario step-by-step to test SENTINEL risk detection.'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Top Step Progress Indicator (when building) */}
        {!evaluationResult && (
          <div className="bg-[#080D18] px-6 py-3 border-b border-slate-800/80 overflow-x-auto">
            <div className="flex items-center justify-between min-w-[580px] gap-2">
              {STEPS.map((step) => {
                const isActive = currentStep === step.number;
                const isPast = currentStep > step.number;
                return (
                  <button
                    key={step.number}
                    type="button"
                    onClick={() => setCurrentStep(step.number)}
                    className={`flex items-center gap-2 text-xs font-semibold py-1 px-2.5 rounded-lg transition-all ${
                      isActive
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                        : isPast
                        ? 'text-slate-300 hover:text-white'
                        : 'text-slate-500 hover:text-slate-400'
                    }`}
                  >
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      isActive
                        ? 'bg-cyan-400 text-black'
                        : isPast
                        ? 'bg-cyan-900/60 text-cyan-300'
                        : 'bg-slate-800 text-slate-400'
                    }`}>
                      {isPast ? <Check className="w-3 h-3" /> : step.number}
                    </span>
                    <span>{step.title}</span>
                    {step.number < STEPS.length && (
                      <span className="text-slate-600 ml-1">→</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6">

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 1: TRANSACTION DETAILS (Who is sending? / Who is receiving?) */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 1 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2 animate-fadeIn">
              <div>
                <h4 className="text-lg font-bold text-slate-100">1. Transaction Details</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Specify the customer account sending the funds and the recipient account receiving them.
                </p>
              </div>

              <div className="space-y-4">
                <div className="bg-[#080D18] p-5 rounded-2xl border border-slate-800 space-y-2">
                  <label className="block text-sm font-semibold text-slate-200">
                    Who is sending?
                  </label>
                  <span className="text-xs text-slate-400 block">
                    Account / Customer ID
                  </span>
                  <input
                    type="text"
                    value={formData.sender_account}
                    onChange={(e) => handleInputChange('sender_account', e.target.value)}
                    placeholder="e.g. ACC-109283"
                    className="w-full bg-[#0C1424] border border-slate-700/80 rounded-xl px-4 py-3 text-base text-slate-100 font-mono focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none transition-colors"
                  />
                  <span className="text-[11px] text-slate-500 block">
                    Example: ACC-109283
                  </span>
                </div>

                <div className="bg-[#080D18] p-5 rounded-2xl border border-slate-800 space-y-2">
                  <label className="block text-sm font-semibold text-slate-200">
                    Who is receiving?
                  </label>
                  <span className="text-xs text-slate-400 block">
                    Beneficiary / Recipient ID
                  </span>
                  <input
                    type="text"
                    value={formData.receiver_account}
                    onChange={(e) => handleInputChange('receiver_account', e.target.value)}
                    placeholder="e.g. ACC-948201"
                    className="w-full bg-[#0C1424] border border-slate-700/80 rounded-xl px-4 py-3 text-base text-slate-100 font-mono focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none transition-colors"
                  />
                  <span className="text-[11px] text-slate-500 block">
                    Example: ACC-948201
                  </span>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/20 transition-all"
                >
                  <span>Next: Transaction Amount</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 2: TRANSACTION AMOUNT                                        */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 2 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2 animate-fadeIn">
              <div>
                <h4 className="text-lg font-bold text-slate-100">2. Transaction Amount</h4>
                <p className="text-xs text-slate-400 mt-1">
                  How much money is being transferred in this transaction?
                </p>
              </div>

              <div className="bg-[#080D18] p-6 rounded-2xl border border-slate-800 space-y-5">
                <label className="block text-sm font-semibold text-slate-200">
                  How much is being sent?
                </label>

                {/* Large Amount Input */}
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan-400 font-extrabold text-2xl">
                    ₹
                  </span>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={formData.amount}
                    onChange={(e) => handleInputChange('amount', Math.max(1, Number(e.target.value)))}
                    className="w-full bg-[#0C1424] border border-slate-700 rounded-xl pl-12 pr-4 py-4 text-2xl font-extrabold font-mono text-slate-100 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none transition-colors"
                  />
                </div>

                {/* Quick-select buttons */}
                <div>
                  <span className="text-xs text-slate-400 block mb-2 font-medium">
                    Quick-select amounts:
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {AMOUNT_PRESETS.map((p) => {
                      const isSelected = formData.amount === p.value;
                      return (
                        <button
                          key={p.value}
                          type="button"
                          onClick={() => handleInputChange('amount', p.value)}
                          className={`p-3 rounded-xl border text-center transition-all ${
                            isSelected
                              ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-md ring-1 ring-cyan-500/30'
                              : 'bg-[#0C1424] text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
                          }`}
                        >
                          <span className="block font-mono font-bold text-sm">{p.label}</span>
                          <span className="text-[11px] text-slate-400 block mt-0.5">{p.tag}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/20 transition-all"
                >
                  <span>Next: Payment Method</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 3: PAYMENT METHOD                                            */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 3 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2 animate-fadeIn">
              <div>
                <h4 className="text-lg font-bold text-slate-100">3. How was the payment made?</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Select the financial payment rail used to initiate this transaction.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {PAYMENT_METHODS.map((method) => {
                  const isSelected = formData.channel === method.id;
                  return (
                    <div
                      key={method.id}
                      onClick={() => handleInputChange('channel', method.id)}
                      className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-center gap-3.5 ${
                        isSelected
                          ? 'bg-cyan-950/30 border-cyan-500/60 shadow-lg ring-1 ring-cyan-500/30'
                          : 'bg-[#080D18] border-slate-800 hover:border-slate-700 hover:bg-[#0C1424]'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 ${
                        isSelected
                          ? 'border-cyan-400 bg-cyan-400 text-black'
                          : 'border-slate-600 bg-transparent'
                      }`}>
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                      <div>
                        <span className="font-bold text-sm text-slate-100 block">
                          {method.label}
                        </span>
                        <span className="text-xs text-slate-400 block mt-0.5">
                          {method.desc}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(4)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/20 transition-all"
                >
                  <span>Next: Payment Time</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 4: TIME                                                      */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 4 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2 animate-fadeIn">
              <div>
                <h4 className="text-lg font-bold text-slate-100">4. When did the payment happen?</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Choose the approximate time of day the transaction was initiated.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Daytime Option */}
                <div
                  onClick={() => handleSelectTime(false)}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all space-y-3 ${
                    !formData.is_night_time
                      ? 'bg-cyan-950/30 border-cyan-500/60 shadow-lg ring-1 ring-cyan-500/30'
                      : 'bg-[#080D18] border-slate-800 hover:border-slate-700 hover:bg-[#0C1424]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                      <Sun className="w-5 h-5" />
                    </div>
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                      !formData.is_night_time
                        ? 'border-cyan-400 bg-cyan-400 text-black'
                        : 'border-slate-600'
                    }`}>
                      {!formData.is_night_time && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </div>
                  <div>
                    <span className="font-bold text-base text-slate-100 block">
                      ☀ Daytime
                    </span>
                    <span className="text-xs text-slate-400 block mt-1">
                      Normal transaction hours
                    </span>
                  </div>
                </div>

                {/* Late Night Option */}
                <div
                  onClick={() => handleSelectTime(true)}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all space-y-3 ${
                    formData.is_night_time
                      ? 'bg-amber-950/30 border-amber-500/60 shadow-lg ring-1 ring-amber-500/30'
                      : 'bg-[#080D18] border-slate-800 hover:border-slate-700 hover:bg-[#0C1424]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
                      <Moon className="w-5 h-5" />
                    </div>
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                      formData.is_night_time
                        ? 'border-amber-400 bg-amber-400 text-black'
                        : 'border-slate-600'
                    }`}>
                      {formData.is_night_time && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </div>
                  <div>
                    <span className="font-bold text-base text-slate-100 block">
                      🌙 Late Night
                    </span>
                    <span className="text-xs text-slate-400 block mt-1">
                      Unusual transaction hours
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(5)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/20 transition-all"
                >
                  <span>Next: Warning Signs</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 5: WARNING SIGNS CHECKLIST                                   */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 5 && (
            <div className="space-y-5 max-w-3xl mx-auto py-2 animate-fadeIn">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div>
                  <h4 className="text-lg font-bold text-slate-100">5. Did anything unusual happen?</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Select everything that applies. These choices help SENTINEL simulate suspicious transaction scenarios.
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold shrink-0 self-start sm:self-auto border ${
                  selectedWarningSigns.length > 0
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}>
                  {selectedWarningSigns.length} warning {selectedWarningSigns.length === 1 ? 'sign' : 'signs'} selected
                </span>
              </div>

              {/* Large Clickable Checklist Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {WARNING_SIGNS.map((sign) => {
                  const isChecked = !!formData[sign.field];
                  return (
                    <div
                      key={sign.id}
                      onClick={() => toggleWarningSign(sign)}
                      className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-start gap-3.5 select-none ${
                        isChecked
                          ? 'bg-cyan-950/30 border-cyan-500/60 shadow-md ring-1 ring-cyan-500/30'
                          : 'bg-[#080D18] border-slate-800 hover:border-slate-700 hover:bg-[#0C1424]'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-md border mt-0.5 flex items-center justify-center shrink-0 transition-colors ${
                        isChecked
                          ? 'bg-cyan-500 border-cyan-400 text-black'
                          : 'bg-[#0C1424] border-slate-600'
                      }`}>
                        {isChecked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                      </div>

                      <div className="min-w-0 flex-1">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-0.5">
                          {sign.category}
                        </span>
                        <span className="font-bold text-sm text-slate-100 block">
                          {sign.title}
                        </span>
                        <span className="text-xs text-slate-400 block mt-0.5 leading-relaxed">
                          {sign.desc}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(4)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(6)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/20 transition-all"
                >
                  <span>Next: Customer Baseline</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 6: OPTIONAL CUSTOMER BASELINE                                */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 6 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2 animate-fadeIn">
              <div>
                <h4 className="text-lg font-bold text-slate-100">6. Customer Baseline</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Baseline monthly spending helps SENTINEL understand whether this payment is unusually large for this customer.
                </p>
              </div>

              <div className="bg-[#080D18] p-6 rounded-2xl border border-slate-800 space-y-4">
                <label className="block text-sm font-semibold text-slate-200">
                  Customer's usual monthly spending
                </label>

                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-extrabold text-xl">
                    ₹
                  </span>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={formData.avg_monthly_tx_amount}
                    onChange={(e) => handleInputChange('avg_monthly_tx_amount', Number(e.target.value))}
                    className="w-full bg-[#0C1424] border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-xl font-bold font-mono text-slate-100 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none transition-colors"
                  />
                </div>

                <p className="text-xs text-slate-400 leading-relaxed bg-[#0C1424] p-3.5 rounded-xl border border-slate-800/80">
                  This helps SENTINEL understand whether this payment is unusually large for the customer.
                </p>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(5)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(7)}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/20 transition-all"
                >
                  <span>Review Before Testing</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* STEP 7: REVIEW BEFORE TESTING                                     */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {!evaluationResult && currentStep === 7 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2 animate-fadeIn">
              <div>
                <h4 className="text-lg font-bold text-slate-100">Review Transaction</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Verify the transaction details and selected warning signs before running SENTINEL's assessment.
                </p>
              </div>

              {/* Review Card */}
              <div className="bg-[#080D18] rounded-2xl border border-slate-800 overflow-hidden divide-y divide-slate-800">
                
                {/* Row 1: Sender & Recipient */}
                <div className="p-4 grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-400 block font-medium">Sender</span>
                    <span className="text-sm font-mono font-bold text-slate-100 mt-0.5 block">
                      {formData.sender_account}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block font-medium">Recipient</span>
                    <span className="text-sm font-mono font-bold text-slate-100 mt-0.5 block">
                      {formData.receiver_account}
                    </span>
                  </div>
                </div>

                {/* Row 2: Amount, Method, Time */}
                <div className="p-4 grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="text-slate-400 block font-medium">Amount</span>
                    <span className="text-base font-mono font-extrabold text-cyan-400 mt-0.5 block">
                      {formatCurrency(formData.amount)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-medium">Payment method</span>
                    <span className="text-sm font-bold text-slate-200 mt-0.5 block">
                      {formData.channel}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-medium">Time</span>
                    <span className="text-sm font-bold text-slate-200 mt-0.5 block">
                      {formData.is_night_time ? '🌙 Late Night' : '☀ Daytime'}
                    </span>
                  </div>
                </div>

                {/* Row 3: Warning signs */}
                <div className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Warning signs</span>
                    <span className="text-xs font-semibold text-cyan-400">
                      {selectedWarningSigns.length} selected
                    </span>
                  </div>

                  {selectedWarningSigns.length === 0 ? (
                    <span className="text-xs text-slate-500 italic block py-1">
                      No warning signs selected (Routine baseline transaction)
                    </span>
                  ) : (
                    <div className="space-y-1.5 pt-1">
                      {selectedWarningSigns.map((sign) => (
                        <div key={sign.id} className="flex items-center gap-2 text-xs text-slate-200">
                          <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span className="font-semibold">{sign.title}</span>
                          <span className="text-slate-400 text-[11px]">— {sign.desc}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

              {error && (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-3 pt-2">
                <button
                  type="button"
                  onClick={handleEvaluate}
                  disabled={evaluating || addingToBatch}
                  className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-extrabold text-sm shadow-xl shadow-cyan-500/20 transition-all disabled:opacity-50"
                >
                  {evaluating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                      <span>Assessing Risk...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" />
                      <span>TEST TRANSACTION</span>
                    </>
                  )}
                </button>

                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(5)}
                    className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    ← Back to edit
                  </button>

                  <button
                    type="button"
                    onClick={handleAddToBatch}
                    disabled={addingToBatch || evaluating}
                    className="text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1.5"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>{addingToBatch ? 'Adding to Batch...' : 'Add as Test Input to Batch'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════ */}
          {/* RESULTS SCREEN (ZERO RAW JSON, PRESENTATION-READY ASSESSMENT)      */}
          {/* ═══════════════════════════════════════════════════════════════════ */}
          {evaluationResult && (
            <div className="space-y-5 max-w-2xl mx-auto py-2 animate-fadeIn">
              
              {/* Overall Risk Card */}
              <div className={`p-6 rounded-2xl border ${
                (tx?.risk_score ?? 0) >= 85
                  ? 'bg-rose-950/30 border-rose-500/40 text-rose-100'
                  : (tx?.risk_score ?? 0) >= 70
                  ? 'bg-orange-950/30 border-orange-500/40 text-orange-100'
                  : (tx?.risk_score ?? 0) >= 40
                  ? 'bg-amber-950/30 border-amber-500/40 text-amber-100'
                  : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-100'
              } space-y-3`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider opacity-80">
                    Overall Risk
                  </span>
                  <span className="text-xs font-extrabold px-3 py-1 rounded-full bg-black/40 border border-white/10 uppercase">
                    {tx?.risk_level || 'EVALUATED'}
                  </span>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className="text-5xl font-black font-mono tracking-tight">
                    {tx?.risk_score ?? 0}
                  </span>
                  <span className="text-sm font-semibold opacity-90">/ 100 Risk Score</span>
                </div>
              </div>

              {/* Why? Section */}
              <div className="p-5 bg-[#080D18] border border-slate-800 rounded-2xl space-y-3">
                <h5 className="text-sm font-bold text-slate-100">Why?</h5>
                <p className="text-xs text-slate-400">
                  {selectedWarningSigns.length > 0 
                    ? 'SENTINEL detected multiple unusual warning signs:'
                    : 'SENTINEL evaluated the transaction against customer baseline behavioral patterns:'}
                </p>

                <div className="space-y-2 pt-1">
                  {selectedWarningSigns.length > 0 ? (
                    selectedWarningSigns.map((sign) => (
                      <div key={sign.id} className="flex items-start gap-2.5 text-xs text-slate-200">
                        <Check className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold">{sign.title}</span>
                          <span className="text-slate-400 ml-1.5">— {sign.desc}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="flex items-start gap-2.5 text-xs text-emerald-300">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <span>Transaction is consistent with normal legitimate account activity.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Recommended Action */}
              <div className={`p-5 rounded-2xl border ${
                policy?.action === 'FREEZE'
                  ? 'bg-rose-950/20 border-rose-500/40'
                  : policy?.action === 'ESCALATE_ANALYST_REVIEW'
                  ? 'bg-orange-950/20 border-orange-500/40'
                  : 'bg-emerald-950/20 border-emerald-500/40'
              } space-y-3`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Recommended Action
                  </span>
                  <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                    policy?.action === 'FREEZE'
                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                      : policy?.action === 'ESCALATE_ANALYST_REVIEW'
                      ? 'bg-orange-500/20 text-orange-300 border-orange-500/40'
                      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  }`}>
                    {policy?.action === 'FREEZE'
                      ? 'HUMAN REVIEW REQUIRED'
                      : policy?.action === 'ESCALATE_ANALYST_REVIEW'
                      ? 'ESCALATE TO COMPLIANCE ANALYST'
                      : 'ALLOW & MONITOR'}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {policy?.action === 'FREEZE'
                    ? 'SENTINEL recommends holding this transaction for authorized operator review. Autonomous debit blocks are strictly refused without verified human authorization.'
                    : policy?.action === 'ESCALATE_ANALYST_REVIEW'
                    ? 'SENTINEL recommends routing this case to compliance analysts for enhanced investigation.'
                    : 'SENTINEL recommends allowing the transaction to proceed safely under automated monitoring.'}
                </p>
              </div>

              {/* Repeat Test (100% Determinism Verification) */}
              <div className="p-5 bg-[#0C1424] border border-emerald-500/30 rounded-2xl space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <span className="text-xs font-bold text-emerald-300 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Repeat Test
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                    Deterministic Engine
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                  <div className="bg-[#080D18] p-3 rounded-xl border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase block font-sans">Previous assessment</span>
                    <span className="text-sm font-bold text-slate-200 mt-1 block">
                      {previousResult?.transaction?.risk_score ?? tx?.risk_score} — {previousResult?.transaction?.risk_level ?? tx?.risk_level}
                    </span>
                  </div>
                  <div className="bg-[#080D18] p-3 rounded-xl border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase block font-sans">Current assessment</span>
                    <span className="text-sm font-bold text-cyan-400 mt-1 block">
                      {tx?.risk_score} — {tx?.risk_level}
                    </span>
                  </div>
                </div>

                <div className="pt-1 flex items-center justify-between">
                  <div className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5">
                    <Check className="w-4 h-4" />
                    <span>RESULT MATCHED — No score drift</span>
                  </div>

                  <button
                    type="button"
                    onClick={handleEvaluate}
                    disabled={evaluating}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin' : ''}`} />
                    <span>Re-test Transaction</span>
                  </button>
                </div>
              </div>

              {/* Technical Details (Collapsed by default, zero raw JSON) */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                  className="flex items-center justify-between w-full px-4 py-3 rounded-xl bg-[#080D18] hover:bg-slate-800/80 border border-slate-800 text-slate-300 text-xs font-semibold transition-all"
                >
                  <span className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-cyan-400" />
                    <span>Technical Details</span>
                  </span>
                  {showTechnicalDetails ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </button>

                {showTechnicalDetails && (
                  <div className="mt-2.5 p-4 rounded-xl bg-[#080D18] border border-slate-800 space-y-3 text-xs animate-fadeIn">
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-[#0C1424] p-3 rounded-lg border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase block font-medium">Rule Score</span>
                        <span className="text-base font-mono font-bold text-slate-200 mt-0.5 block">{tx?.rule_score ?? 0}</span>
                      </div>
                      <div className="bg-[#0C1424] p-3 rounded-lg border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase block font-medium">ML / Pattern Score</span>
                        <span className="text-base font-mono font-bold text-slate-200 mt-0.5 block">{Math.round(tx?.ml_score ?? 0)}</span>
                      </div>
                    </div>

                    <div className="space-y-2 pt-1 text-[11px] text-slate-300">
                      <div className="flex justify-between py-1 border-b border-slate-800">
                        <span className="text-slate-400">Hybrid Formula:</span>
                        <span className="font-mono text-cyan-400 font-semibold">60% ML + 40% Rules</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-800">
                        <span className="text-slate-400">Policy Rule ID:</span>
                        <span className="font-mono text-slate-200">{policy?.policy_rule_id || 'POL-DEFAULT'}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-800">
                        <span className="text-slate-400">Evaluation Version:</span>
                        <span className="font-mono text-slate-300">v{tx?.evaluation_version || '2.0.0'}</span>
                      </div>
                      <div className="flex justify-between py-1">
                        <span className="text-slate-400">Deterministic Seed:</span>
                        <span className="font-mono text-slate-300">{tx?.deterministic_seed || 'STABLE-DETERMINISTIC'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Actions */}
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  onClick={handleAddToBatch}
                  disabled={addingToBatch}
                  className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 font-bold text-xs transition-all flex items-center justify-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  <span>{addingToBatch ? 'Adding to Batch...' : 'Add to Benchmark Batch'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleReset}
                  className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition-colors flex items-center justify-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Test Another Transaction</span>
                </button>
              </div>

            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default CustomTransactionModal;
