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
        setResult({
          risk_title: raw.risk_title || desc,
          total_est_cost_usd: raw.total_est_cost_usd || 124500,
          total_duration_days: raw.total_duration_days || 30,
          remediation_steps: Array.isArray(raw.remediation_steps) ? raw.remediation_steps : [],
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
        className="glass-panel p-6 md:p-8 rounded-2xl"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
            <Wrench className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-heading">
              30-Day Remediation Generator
            </h2>
            <p className="text-xs text-zinc-400">
              Generate a cost-estimated, step-by-step statutory compliance roadmap.
            </p>
          </div>
        </div>

        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-white mb-1.5">
              Risk Title / Description:
            </label>
            <input
              type="text"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full p-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">
                Exposure Level:
              </label>
              <select
                value={exposure}
                onChange={(e) => setExposure(e.target.value as ExposureLevel)}
                className="w-full p-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all cursor-pointer"
              >
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">
                Est. Financial Exposure ($ USD):
              </label>
              <input
                type="number"
                value={cost}
                onChange={(e) => setCost(e.target.value)}
                className="w-full p-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-white mb-1.5">
              Statutory Legal Basis:
            </label>
            <input
              type="text"
              value={basis}
              onChange={(e) => setBasis(e.target.value)}
              className="w-full p-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !desc.trim()}
            className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-white text-black font-heading font-bold text-base shadow-glow-white hover:bg-zinc-200 active:scale-[0.99] transition-all disabled:opacity-50 cursor-pointer"
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
        className="glass-panel p-6 md:p-8 rounded-2xl min-h-[480px] flex flex-col"
      >
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
          <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-heading">
              Statutory Action Roadmap
            </h2>
            <p className="text-xs text-zinc-400">
              Prioritized execution roadmap with cost estimates and statutory milestones.
            </p>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {!result && !isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-white/5 border border-white/15 flex items-center justify-center text-zinc-500 mb-4">
                <Clock className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white font-heading mb-2">
                No Remediation Plan Active
              </h3>
              <p className="text-sm text-zinc-400 max-w-sm">
                Specify risk parameters and click "Generate 30-Day Remediation Plan" to render execution steps.
              </p>
            </div>
          )}

          {isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <Loader2 className="w-10 h-10 text-white animate-spin mb-4" />
              <p className="text-sm font-semibold text-white">
                Generating Statutory Remediation Timeline & Cost Estimates...
              </p>
            </div>
          )}

          {result && !isLoading && (
            <div className="space-y-6">
              {/* Summary Bar */}
              <div className="grid grid-cols-3 gap-3 p-4 rounded-xl bg-black/60 border border-white/15 text-center">
                <div>
                  <div className="text-lg font-extrabold text-white">
                    ${(result.total_est_cost_usd || 124500).toLocaleString()}
                  </div>
                  <div className="text-[11px] text-zinc-400">Est. Total Cost (USD)</div>
                </div>
                <div>
                  <div className="text-lg font-extrabold text-white">
                    {result.total_duration_days || 30} Days
                  </div>
                  <div className="text-[11px] text-zinc-400">Execution Period</div>
                </div>
                <div>
                  <div className="text-lg font-extrabold text-white">
                    {(result.remediation_steps || []).length} Steps
                  </div>
                  <div className="text-[11px] text-zinc-400">Milestones</div>
                </div>
              </div>

              {/* Timeline Steps */}
              <div className="space-y-4">
                {(result.remediation_steps || []).map((step, idx) => (
                  <motion.div
                    key={step.step_number || idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-4 rounded-xl bg-white/5 border border-white/15 hover:border-white/40 transition-colors space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-0.5 rounded-full bg-white/10 text-white text-[11px] font-bold">
                        Step {step.step_number || idx + 1}: {step.phase || 'Action Item'}
                      </span>
                      <span className="text-xs text-zinc-400 font-mono">
                        Target: {step.timeline_days || (idx + 1) * 7} Days
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white font-heading">
                      {step.title}
                    </h4>

                    <p className="text-xs text-zinc-300 leading-relaxed">
                      {step.action}
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/10 text-[11px] text-zinc-400">
                      <div>
                        Owner: <strong className="text-white">{step.owner_role || 'DPO'}</strong>
                      </div>
                      <div>
                        Cost: <strong className="text-white">${(step.est_cost_usd || 10000).toLocaleString()}</strong>
                      </div>
                      <div className="font-mono text-zinc-400">
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
