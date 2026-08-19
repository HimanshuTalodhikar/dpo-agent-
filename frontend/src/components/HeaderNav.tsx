import React from 'react';
import { ShieldCheck, Cpu, ExternalLink, Sparkles } from 'lucide-react';

interface HeaderNavProps {
  serverStatus: 'healthy' | 'checking' | 'error';
}

export const HeaderNav: React.FC<HeaderNavProps> = ({ serverStatus }) => {
  return (
    <header className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-4 p-4 md:px-8 mb-6 glass-panel rounded-2xl">
      {/* Brand & Identity */}
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-xl bg-black border border-white/30 flex items-center justify-center shadow-glow-white">
          <ShieldCheck className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-extrabold tracking-tight text-white font-heading">
              DPDP AI Agent
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-white/10 text-white border border-white/20">
              v2.0 PRO
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-medium">
            Executive Legal AI & Data Privacy Command Center
          </p>
        </div>
      </div>

      {/* Center Status Indicators */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/60 border border-white/15">
          <span
            className={`w-2 h-2 rounded-full ${
              serverStatus === 'healthy'
                ? 'bg-emerald-400 animate-pulse'
                : serverStatus === 'checking'
                ? 'bg-amber-400 animate-ping'
                : 'bg-rose-500'
            }`}
          />
          <span className="text-zinc-300 font-medium">
            AWS ECS Fargate: <strong className="text-white">Active</strong>
          </span>
        </div>

        <a
          href="https://www.digiprotect.ai"
          target="_blank"
          rel="noreferrer"
          className="hidden sm:flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors"
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>digiprotect.ai</span>
          <ExternalLink className="w-3 h-3 opacity-60" />
        </a>
      </div>

      {/* User / Org Profile */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/15">
          <div className="w-7 h-7 rounded-full bg-black border border-white/40 flex items-center justify-center text-xs font-bold text-white">
            FS
          </div>
          <div className="text-left hidden lg:block">
            <div className="text-xs font-semibold text-white leading-tight">
              Fintech Solutions Ltd (India)
            </div>
            <div className="text-[10px] text-zinc-400">Chief Legal Officer</div>
          </div>
        </div>

        <div className="px-3 py-1.5 text-xs font-semibold rounded-full bg-white text-black flex items-center gap-1.5 shadow-glow-white">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Codemax AI</span>
        </div>
      </div>
    </header>
  );
};
