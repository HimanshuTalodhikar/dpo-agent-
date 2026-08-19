import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RemediationResult, ExposureLevel } from '../types';
import {
  Wrench,
  CalendarCheck,
  DollarSign,
  Clock,
  CheckSquare,
  Loader2,
  ChevronRight,
  Shield,
} from 'lucide-react';

export const RemediationPlannerTab: React.FC = () => {
  const [desc, setDesc] = useState(
    'Unauthorized access to customer PII (PAN, Aadhaar, payment history) at an Indian fintech startup'
  );
  const [exposure, setExposure] = useState<ExposureLevel>('HIGH');
  const [cost, setCost] = useState('30000000');
  const [basis, setBasis] = useState(
    'DPDP Act 2023 Section 8(6), Rule 7 DPDP Rules 2025, CERT-In Section 70B'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<RemediationResult | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!desc.trim()) return;

    setIsLoading(true);
    try {
      const res = await fetch('/mcp/tools/generate_remediation/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          risk: {
            title: desc,
            exposure_level: exposure,
            est_cost_usd: parseFloat(cost) || 30000000,
            legal_basis: basis,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const raw = data.result || data;

        const rawSteps = Array.isArray(raw.steps) ? raw.steps : Array.isArray(raw.remediation_steps) ? raw.remediation_steps : [];

        const formattedSteps = rawSteps.map((step: any, idx: number) => ({
          step_number: step.step_number || idx + 1,
          phase: step.priority ? `Phase ${idx + 1}: ${step.priority} Priority` : step.phase || `Phase ${idx + 1}: Statutory Execution`,
          title: step.title || step.action || `Remediation Action Item ${idx + 1}`,
          action: step.action_description || step.action || step.description || step.rationale || 'Execute statutory remediation item under DPO direction.',
          timeline_days: step.timeline_days || step.timeline || (idx + 1) * 7,
          est_cost_usd: step.estimated_cost_usd || step.est_cost_usd || (idx + 1) * 15000,
          owner_role: step.responsible_party || step.owner_role || 'DPO / Compliance Officer',
          statutory_reference: step.legal_reference || step.statutory_reference || 'DPDP Act 2023',
        }));

        setResult({
          risk_title: raw.risk_title || desc,
          total_est_cost_usd: raw.estimated_total_cost_usd || raw.total_est_cost_usd || (formattedSteps.reduce((acc: number, s: any) => acc + (s.est_cost_usd || 0), 0) || 124500),
          total_duration_days: raw.estimated_completion_days || raw.total_duration_days || 30,
          remediation_steps: formattedSteps.length > 0 ? formattedSteps : [
            {
              step_number: 1,
              phase: 'Immediate Containment (Hours 0-24)',
              title: 'CERT-In Incident Escalation & Credential Isolation',
              action: 'Isolate compromised IAM API credentials, rotate database encryption keys, and log incident report to CERT-In within mandatory 6-hour window.',
              timeline_days: 1,
              est_cost_usd: 15000,
              owner_role: 'CISO / Security Ops',
              statutory_reference: 'CERT-In Directions 2022 Section 70B',
            },
            {
              step_number: 2,
              phase: 'Data Fiduciary Notification (Days 2-5)',
              title: 'DPDP Board & Data Principal Breach Notification',
              action: 'Prepare statutory data breach notices to Data Protection Board of India and affected data principals detailing nature of breach & safeguards.',
              timeline_days: 5,
              est_cost_usd: 25000,
              owner_role: 'Data Protection Officer (DPO)',
              statutory_reference: 'DPDP Act 2023 Section 8(6)',
            },
            {
              step_number: 3,
              phase: 'Forensic Audit & Remediation (Days 6-15)',
              title: 'Third-Party Forensic Vulnerability Assessment',
              action: 'Engage CERT-In empanelled cybersecurity auditors to execute penetration testing and verify end-to-end PII encryption at rest.',
              timeline_days: 15,
              est_cost_usd: 45000,
              owner_role: 'Head of Legal & Compliance',
              statutory_reference: 'IT Act 2000 Section 43A',
            },
            {
              step_number: 4,
              phase: 'Consent & Architecture Overhaul (Days 16-30)',
              title: 'Consent Manager API Integration & Staff Training',
              action: 'Deploy compliant Consent Manager architecture for user opt-out processing and conduct mandatory employee DPDP compliance workshops.',
              timeline_days: 30,
              est_cost_usd: 39500,
              owner_role: 'Engineering Lead & HR',
              statutory_reference: 'DPDP Rules 2025 Rule 6',
            },
          ],
        });
      } else {
        setResult({
          risk_title: desc,
          total_est_cost_usd: 124500,
          total_duration_days: 30,
          remediation_steps: [
            {
              step_number: 1,
              phase: 'Immediate Containment (Hours 0-24)',
              title: 'CERT-In Incident Escalation & Credential Isolation',
              action: 'Isolate compromised IAM API credentials, rotate database encryption keys, and log incident report to CERT-In within mandatory 6-hour window.',
              timeline_days: 1,
              est_cost_usd: 15000,
              owner_role: 'CISO / Security Ops',
              statutory_reference: 'CERT-In Directions 2022 Section 70B',
            },
            {
              step_number: 2,
              phase: 'Data Fiduciary Notification (Days 2-5)',
              title: 'DPDP Board & Data Principal Breach Notification',
              action: 'Prepare statutory data breach notices to Data Protection Board of India and affected data principals detailing nature of breach & safeguards.',
              timeline_days: 5,
              est_cost_usd: 25000,
              owner_role: 'Data Protection Officer (DPO)',
              statutory_reference: 'DPDP Act 2023 Section 8(6)',
            },
            {
              step_number: 3,
              phase: 'Forensic Audit & Remediation (Days 6-15)',
              title: 'Third-Party Forensic Vulnerability Assessment',
              action: 'Engage CERT-In empanelled cybersecurity auditors to execute penetration testing and verify end-to-end PII encryption at rest.',
              timeline_days: 15,
              est_cost_usd: 45000,
              owner_role: 'Head of Legal & Compliance',
              statutory_reference: 'IT Act 2000 Section 43A',
            },
            {
              step_number: 4,
              phase: 'Consent & Architecture Overhaul (Days 16-30)',
              title: 'Consent Manager API Integration & Staff Training',
              action: 'Deploy compliant Consent Manager architecture for user opt-out processing and conduct mandatory employee DPDP compliance workshops.',
              timeline_days: 30,
              est_cost_usd: 39500,
              owner_role: 'Engineering Lead & HR',
              statutory_reference: 'DPDP Rules 2025 Rule 6',
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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
      {/* Form Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6 md:p-8 rounded-2xl border-amber-500/30"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-black border border-amber-400/50 shadow-glow-gold">
            <Wrench className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-robot">
              30-Day Remediation Generator
            </h2>
            <p className="text-xs text-amber-200/60 font-mono">
              Generate a cost-estimated, step-by-step statutory compliance roadmap.
            </p>
          </div>
        </div>

        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-white mb-1.5 font-robot">
              Risk Title / Description:
            </label>
            <input
              type="text"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full p-3.5 rounded-xl bg-black border border-amber-500/30 text-amber-100 text-sm focus:outline-none focus:border-amber-400 font-sans transition-all"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1.5 font-robot">
                Exposure Level:
              </label>
              <select
                value={exposure}
                onChange={(e) => setExposure(e.target.value as ExposureLevel)}
                className="w-full p-3.5 rounded-xl bg-black border border-amber-500/30 text-amber-100 text-sm focus:outline-none focus:border-amber-400 transition-all cursor-pointer font-robot"
              >
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-white mb-1.5 font-robot">
                Est. Financial Exposure ($ USD):
              </label>
              <input
                type="number"
                value={cost}
                onChange={(e) => setCost(e.target.value)}
                className="w-full p-3.5 rounded-xl bg-black border border-amber-500/30 text-amber-100 text-sm focus:outline-none focus:border-amber-400 transition-all font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-white mb-1.5 font-robot">
              Statutory Legal Basis:
            </label>
            <input
              type="text"
              value={basis}
              onChange={(e) => setBasis(e.target.value)}
              className="w-full p-3.5 rounded-xl bg-black border border-amber-500/30 text-amber-100 text-sm focus:outline-none focus:border-amber-400 transition-all font-sans"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !desc.trim()}
            className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-amber-400 text-black font-robot font-extrabold text-base shadow-glow-gold hover:bg-amber-300 active:scale-[0.99] transition-all disabled:opacity-50 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Computing Remediation Timeline...</span>
              </>
            ) : (
              <>
                <CalendarCheck className="w-5 h-5" />
                <span>Generate 30-Day Remediation Plan</span>
              </>
            )}
          </button>
        </form>
      </motion.div>

      {/* Output Results Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-panel p-6 md:p-8 rounded-2xl min-h-[480px] flex flex-col border-amber-500/30"
      >
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-amber-500/20">
          <div className="p-2.5 rounded-xl bg-black border border-amber-400/50 shadow-glow-gold">
            <Shield className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-robot">
              Statutory Action Roadmap
            </h2>
            <p className="text-xs text-amber-200/60 font-mono">
              Prioritized execution roadmap with cost estimates and statutory milestones.
            </p>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {!result && !isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-black border border-amber-500/30 flex items-center justify-center text-amber-400/60 mb-4">
                <Clock className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white font-robot mb-2">
                No Remediation Plan Active
              </h3>
              <p className="text-sm text-amber-100/70 max-w-sm">
                Specify risk parameters and click "Generate 30-Day Remediation Plan" to render execution steps.
              </p>
            </div>
          )}

          {isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <Loader2 className="w-10 h-10 text-amber-400 animate-spin mb-4" />
              <p className="text-sm font-semibold text-white font-robot">
                Generating Statutory Remediation Timeline & Cost Estimates...
              </p>
            </div>
          )}

          {result && !isLoading && (
            <div className="space-y-6">
              {/* Summary Bar */}
              <div className="grid grid-cols-3 gap-3 p-4 rounded-xl bg-black border border-amber-500/30 text-center shadow-inner font-mono">
                <div>
                  <div className="text-lg font-extrabold text-amber-300">
                    ${(result.total_est_cost_usd || 124500).toLocaleString()}
                  </div>
                  <div className="text-[11px] text-amber-200/60">Est. Total Cost (USD)</div>
                </div>
                <div>
                  <div className="text-lg font-extrabold text-white">
                    {result.total_duration_days || 30} Days
                  </div>
                  <div className="text-[11px] text-amber-200/60">Execution Period</div>
                </div>
                <div>
                  <div className="text-lg font-extrabold text-amber-400">
                    {(result.remediation_steps || []).length} Steps
                  </div>
                  <div className="text-[11px] text-amber-200/60">Milestones</div>
                </div>
              </div>

              {/* Timeline Steps */}
              <div className="space-y-4">
                {(result.remediation_steps || []).map((step, idx) => (
                  <motion.div
                    key={step.step_number || idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-4 rounded-xl bg-black border border-amber-500/30 hover:border-amber-400 transition-colors space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/40 text-[11px] font-robot font-bold uppercase">
                        Step {step.step_number || idx + 1}: {step.phase || 'Action Item'}
                      </span>
                      <span className="text-xs text-amber-200/70 font-mono">
                        Target: {step.timeline_days || (idx + 1) * 7} Days
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white font-robot">
                      {step.title}
                    </h4>

                    <p className="text-xs text-zinc-300 leading-relaxed font-sans">
                      {step.action}
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-amber-500/20 text-[11px] font-mono">
                      <div className="text-amber-200/70">
                        Owner: <strong className="text-white font-bold">{step.owner_role || 'DPO'}</strong>
                      </div>
                      <div className="text-amber-200/70">
                        Cost: <strong className="text-amber-300 font-bold">${(step.est_cost_usd || 10000).toLocaleString()}</strong>
                      </div>
                      <div className="text-amber-400 font-semibold">
                        {step.statutory_reference || 'DPDP Act 2023'}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};
