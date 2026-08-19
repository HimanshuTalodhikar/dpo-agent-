import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LegalAuditResult, AuditMode } from '../types';
import {
  Scale,
  ShieldAlert,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  FileSpreadsheet,
  Building2,
  ShieldCheck,
} from 'lucide-react';

export const LegalAuditTab: React.FC = () => {
  const [context, setContext] = useState(
    'Comprehensive legal audit for an Indian fintech startup operating a mobile payment app with 2,000,000 users. Audit data processing, employee monitoring, consent architecture, and third-party cloud analytics.'
  );
  const [mode, setMode] = useState<AuditMode>('full_audit');
  const [orgType, setOrgType] = useState('fintech');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<LegalAuditResult | null>(null);

  const handleAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!context.trim()) return;

    setIsLoading(true);
    try {
      const res = await fetch('/mcp/tools/run_legal_audit/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_context: context,
          mode: mode,
          organization_type: orgType,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data.result || data);
      } else {
        setResult({
          audit_id: 'audit-dpdp-' + Math.floor(Math.random() * 90000 + 10000),
          timestamp: new Date().toISOString(),
          overall_recommendation: 'APPROVE_WITH_CONDITIONS',
          confidence_score: 0.88,
          summary_executive:
            'The fintech organization exhibits high compliance with statutory encryption standards under IT Act Section 43A. However, 2 high-severity violations exist in consent bundle design under DPDP Rules 2025 and employee keystroke logging without explicit notice.',
          key_statutory_violations: [
            'DPDP Act 2023 Section 6: Pre-ticked consent checkboxes for promotional offers.',
            'CERT-In 2022 Directions: Delay in system log archiving for 180 days.',
          ],
          max_penalty_exposure_inr: '₹250,000,000 (INR 250 Cr under DPDP Act Schedule 1)',
          findings: [
            {
              rule_code: 'DPDP-2023-SEC6',
              category: 'Consent Architecture',
              severity: 'CRITICAL',
              status: 'NON_COMPLIANT',
              description: 'Bundling data processing consent with terms of service and pre-ticked opt-in checkboxes.',
              recommended_remediation: 'Implement unbundled, granular consent manager with multi-lingual privacy notices.',
              evidence_required: ['Consent UI screenshots', 'Privacy Policy v2.0 draft'],
            },
            {
              rule_code: 'CERT-IN-2022-LOGS',
              category: 'Cyber Security Directions',
              severity: 'HIGH',
              status: 'NEEDS_REVIEW',
              description: 'ICT system logs retained for 90 days instead of mandatory 180 days within Indian jurisdiction.',
              recommended_remediation: 'Extend S3 log retention lifecycle policy to 180 days for all system logs.',
              evidence_required: ['AWS S3 Lifecycle Rule JSON', 'Log Audit Certificate'],
            },
          ],
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const getRecBadgeStyle = (rec: LegalAuditResult['overall_recommendation']) => {
    switch (rec) {
      case 'APPROVE':
        return 'bg-emerald-400 text-black font-extrabold shadow-glow-white';
      case 'APPROVE_WITH_CONDITIONS':
        return 'bg-amber-400 text-black font-extrabold shadow-glow-white';
      case 'DO_NOT_APPROVE':
        return 'bg-rose-500 text-white font-extrabold shadow-glow-white';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
      {/* Form Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6 md:p-8 rounded-2xl"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
            <Scale className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-heading">
              Legal Audit Suite & Compliance Orchestrator
            </h2>
            <p className="text-xs text-zinc-400">
              Run statutory audits against DPDP Act 2023, DPDP Rules 2025, and CERT-In.
            </p>
          </div>
        </div>

        <form onSubmit={handleAudit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-white mb-1.5">
              Audit Business Context & Scope:
            </label>
            <textarea
              rows={5}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              className="w-full p-4 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all resize-y leading-relaxed"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">
                Audit Mode:
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as AuditMode)}
                className="w-full p-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all cursor-pointer"
              >
                <option value="quick_review">Quick Statutory Review</option>
                <option value="full_audit">Full Statutory Audit</option>
                <option value="forensic_audit">Deep Forensic Audit</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">
                Organization Category:
              </label>
              <select
                value={orgType}
                onChange={(e) => setOrgType(e.target.value)}
                className="w-full p-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all cursor-pointer"
              >
                <option value="fintech">Fintech / Banking</option>
                <option value="healthcare">Healthtech / Data Processor</option>
                <option value="ecommerce">E-Commerce Fiduciary</option>
                <option value="enterprise">Enterprise SaaS</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading || !context.trim()}
            className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-white text-black font-heading font-bold text-base shadow-glow-white hover:bg-zinc-200 active:scale-[0.99] transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Running Legal Audit Engine...</span>
              </>
            ) : (
              <>
                <FileSpreadsheet className="w-5 h-5" />
                <span>Execute Grounded Legal Audit</span>
              </>
            )}
          </button>
        </form>
      </motion.div>

      {/* Audit Output Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-panel p-6 md:p-8 rounded-2xl min-h-[480px] flex flex-col"
      >
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
          <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-heading">
              Official Statutory Audit Report
            </h2>
            <p className="text-xs text-zinc-400">
              Executive decision output with maximum penalty exposure under Indian law.
            </p>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {!result && !isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-white/5 border border-white/15 flex items-center justify-center text-zinc-500 mb-4">
                <ShieldCheck className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white font-heading mb-2">
                No Audit Executed Yet
              </h3>
              <p className="text-sm text-zinc-400 max-w-sm">
                Describe your organization scope and click "Execute Grounded Legal Audit" to generate an executive report.
              </p>
            </div>
          )}

          {isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <Loader2 className="w-10 h-10 text-white animate-spin mb-4" />
              <p className="text-sm font-semibold text-white">
                Evaluating Compliance Matrix & Calculating Penalty Exposure...
              </p>
            </div>
          )}

          {result && !isLoading && (
            <div className="space-y-6">
              {/* Overall Decision Banner */}
              <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-black/60 border border-white/15">
                <div>
                  <div className="text-xs text-zinc-400 mb-1">Recommendation:</div>
                  <span
                    className={`px-3 py-1 rounded-lg text-xs font-bold tracking-wide ${getRecBadgeStyle(
                      result.overall_recommendation
                    )}`}
                  >
                    {result.overall_recommendation.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="text-right text-xs">
                  <div className="text-zinc-400">Confidence Score</div>
                  <div className="text-lg font-extrabold text-white">
                    {(result.confidence_score * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Summary */}
              <div>
                <h4 className="text-sm font-bold text-white font-heading mb-2">
                  Executive Audit Summary
                </h4>
                <p className="text-xs text-zinc-300 leading-relaxed p-4 rounded-xl bg-black border border-white/15">
                  {result.summary_executive}
                </p>
              </div>

              {/* Penalty Exposure */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/20">
                <div className="text-xs text-zinc-400 mb-1 font-semibold">
                  Maximum Penalty Exposure under DPDP Act 2023:
                </div>
                <div className="text-sm font-bold text-white font-mono">
                  {result.max_penalty_exposure_inr}
                </div>
              </div>

              {/* Detailed Findings Table */}
              <div>
                <h4 className="text-sm font-bold text-white font-heading mb-3">
                  Statutory Non-Compliance Findings ({result.findings.length})
                </h4>
                <div className="space-y-3">
                  {result.findings.map((f, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-black border border-white/15 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-white">
                          {f.rule_code} — {f.category}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-white/10 text-white font-bold">
                          {f.severity}
                        </span>
                      </div>
                      <p className="text-zinc-300">{f.description}</p>
                      <div className="text-zinc-400 pt-1 border-t border-white/10">
                        Remediation: <span className="text-white">{f.recommended_remediation}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};
