import React from 'react';
import { ShieldCheck, Cpu, ExternalLink, Sparkles } from 'lucide-react';
import { TabType } from '../types';

interface HeaderNavProps {
  serverStatus: 'healthy' | 'checking' | 'error';
  onNavigateHome?: () => void;
}

export const HeaderNav: React.FC<HeaderNavProps> = ({ serverStatus, onNavigateHome }) => {
  return (
    <header className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-4 p-4 md:px-8 mb-6 glass-panel rounded-2xl border-amber-500/30">
      {/* Brand & Identity — Clickable to return Home */}
      <div
        onClick={onNavigateHome}
        className="flex items-center gap-3 cursor-pointer group"
        title="Return to Main Landing Overview"
      >
        <div className="w-11 h-11 rounded-xl bg-black border border-amber-400/50 flex items-center justify-center shadow-glow-gold group-hover:border-amber-300 transition-all">
          <ShieldCheck className="w-6 h-6 text-amber-400 group-hover:scale-110 transition-transform" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-extrabold tracking-tight text-white font-robot uppercase group-hover:text-amber-300 transition-colors">
              DPDP <span className="text-amber-400">AI AGENT</span>
            </h1>
            <span className="px-2 py-0.5 text-xs font-robot font-bold rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/40">
              v2.0 PRO
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-medium">
            Executive Legal AI & Data Privacy Command Center
          </p>
        </div>
      </div>

      {/* Center Status Indicators */}
      <div className="flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-black/80 border border-amber-500/30">
          <span
            className={`w-2 h-2 rounded-full ${
              serverStatus === 'healthy'
                ? 'bg-amber-400 animate-pulse'
                : serverStatus === 'checking'
                ? 'bg-yellow-300 animate-ping'
                : 'bg-rose-500'
            }`}
          />
          <span className="text-zinc-300">
            AWS ECS Fargate: <strong className="text-amber-400 font-bold">Active</strong>
          </span>
        </div>

        <a
          href="https://www.digiprotect.ai"
          target="_blank"
          rel="noreferrer"
          className="hidden sm:flex items-center gap-1.5 text-zinc-400 hover:text-amber-300 transition-colors"
        >
          <Cpu className="w-3.5 h-3.5 text-amber-400" />
          <span>digiprotect.ai</span>
          <ExternalLink className="w-3 h-3 opacity-60" />
        </a>
      </div>

      {/* User / Org Profile */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-amber-950/40 border border-amber-500/30">
          <div className="w-7 h-7 rounded-full bg-black border border-amber-400 flex items-center justify-center text-xs font-bold text-amber-400 font-robot">
            FS
          </div>
          <div className="text-left hidden lg:block">
            <div className="text-xs font-bold text-white leading-tight font-heading">
              Fintech Solutions Ltd (India)
            </div>
            <div className="text-[10px] text-amber-400/80 font-mono">Chief Legal Officer</div>
          </div>
        </div>

        <div className="px-3.5 py-1.5 text-xs font-robot font-bold rounded-full bg-amber-400 text-black flex items-center gap-1.5 shadow-glow-gold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Codemax AI</span>
        </div>
      </div>
    </header>
  );
};
