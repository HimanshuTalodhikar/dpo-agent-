import React from 'react';
import { motion } from 'framer-motion';
import {
  Gavel,
  CalendarCheck,
  Scale,
  Search,
  FileCheck,
  MessageSquare,
  Plug,
  ArrowRight,
  ShieldCheck,
  Zap,
  Lock,
  Database,
  Terminal,
  Cpu,
} from 'lucide-react';
import { TabType } from '../types';

interface LandingHeroProps {
  onLaunchTool: (tab: TabType) => void;
}

export const LandingHero: React.FC<LandingHeroProps> = ({ onLaunchTool }) => {
  return (
    <div className="space-y-12 mb-12">
      {/* Hero Headline Section */}
      <section className="relative z-10 text-center max-w-4xl mx-auto space-y-6 pt-4">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-400/10 border border-amber-400/40 text-amber-300 text-xs font-robot font-bold tracking-widest uppercase shadow-glow-gold"
        >
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>India's Premier DPDP Act 2023 & Rules 2025 AI Command Platform</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-3xl sm:text-5xl lg:text-6xl font-black text-white font-robot leading-tight tracking-tight uppercase"
        >
          EXECUTIVE LEGAL AI & <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-amber-400 to-yellow-500">
            DATA PRIVACY AUTOMATION
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-sm sm:text-base text-amber-100/80 max-w-2xl mx-auto leading-relaxed font-sans"
        >
          Instantly evaluate corporate legal risk under India's Digital Personal Data Protection Act 2023, DPDP Rules 2025, CERT-In Directions, and IT Act 2000 with 100% grounded statutory vector intelligence.
        </motion.p>

        {/* Primary CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4 pt-2"
        >
          <button
            onClick={() => onLaunchTool('risk')}
            className="flex items-center gap-2.5 px-7 py-4 rounded-xl bg-amber-400 text-black font-robot font-extrabold text-sm shadow-glow-gold-lg hover:bg-amber-300 active:scale-[0.98] transition-all cursor-pointer"
          >
            <span>Launch Legal Risk Analyzer</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={() => onLaunchTool('audit')}
            className="flex items-center gap-2.5 px-6 py-4 rounded-xl bg-black border border-amber-500/50 text-amber-300 font-robot font-bold text-sm hover:bg-amber-400/10 hover:border-amber-400 transition-all cursor-pointer"
          >
            <Scale className="w-4 h-4 text-amber-400" />
            <span>Execute Legal Audit Suite</span>
          </button>

          <button
            onClick={() => onLaunchTool('mcp')}
            className="flex items-center gap-2 px-5 py-4 rounded-xl bg-amber-950/40 border border-amber-500/30 text-zinc-300 font-robot text-xs hover:text-white hover:border-amber-400 transition-all cursor-pointer"
          >
            <Plug className="w-4 h-4 text-amber-400" />
            <span>Connect Claude Desktop</span>
          </button>
        </motion.div>
      </section>


      {/* Executive Capabilities Grid */}
      <section className="relative z-10 space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-white font-robot uppercase tracking-wide">
            Enterprise Legal AI Capability Suite
          </h2>
          <p className="text-xs text-amber-200/60 font-mono">
            Powered by Codemax AI, Graphiti Knowledge Graph, and Zep Agent Memory
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            {
              id: 'risk' as TabType,
              title: 'Statutory Risk Analyzer',
              icon: Gavel,
              desc: 'Evaluate corporate compliance exposure across DPDP Act Section 6, 7, 8 & 16 with priority ranks and statutory rationale cards.',
              badge: 'Section 6 & 16 DPDP',
            },
            {
              id: 'remediation' as TabType,
              title: '30-Day Remediation Generator',
              icon: CalendarCheck,
              desc: 'Generate step-by-step statutory execution timelines with cost estimations in USD/INR and responsible owner roles.',
              badge: '30-Day Execution Plan',
            },
            {
              id: 'audit' as TabType,
              title: 'Legal Audit Orchestrator',
              icon: Scale,
              desc: 'Run multi-agent legal audits with overall decision recommendations and maximum penalty exposure calculations (up to ₹250 Cr).',
              badge: 'INR 250 Cr Penalty Matrix',
            },
            {
              id: 'search' as TabType,
              title: 'Statutory Knowledge Base',
              icon: Search,
              desc: 'Perform semantic vector search across Indian privacy statutes, gazette notifications, and CERT-In directions.',
              badge: 'Graphiti Vector Store',
            },
            {
              id: 'ingest' as TabType,
              title: 'Act & Rule Ingestion',
              icon: FileCheck,
              desc: 'Ingest raw statutory PDF gazettes and rules into agent memory with automatic metadata inferencing.',
              badge: 'Zep Memory Pipeline',
            },
            {
              id: 'mcp' as TabType,
              title: 'Model Context Protocol',
              icon: Plug,
              desc: 'Integrate tools directly into Claude Desktop or Cursor IDE via active SSE transport endpoints.',
              badge: 'SSE Transport Live',
            },
          ].map((card) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.id}
                whileHover={{ y: -4 }}
                onClick={() => onLaunchTool(card.id)}
                className="p-6 rounded-2xl glass-panel border-amber-500/30 hover:border-amber-400 transition-all space-y-4 cursor-pointer group flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="p-3 rounded-xl bg-black border border-amber-400/50 shadow-glow-gold group-hover:bg-amber-400 transition-colors">
                      <Icon className="w-5 h-5 text-amber-400 group-hover:text-black transition-colors" />
                    </div>
                    <span className="px-2.5 py-1 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/30 text-[10px] font-robot font-bold uppercase">
                      {card.badge}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-white font-robot group-hover:text-amber-300 transition-colors">
                    {card.title}
                  </h3>

                  <p className="text-xs text-amber-100/70 leading-relaxed font-sans">
                    {card.desc}
                  </p>
                </div>

                <div className="pt-3 border-t border-amber-500/20 flex items-center justify-between text-xs font-robot font-bold text-amber-400 group-hover:text-white transition-colors">
                  <span>Open Tool Module</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
