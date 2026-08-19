import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Scan, ShieldCheck, Zap, Sparkles, Terminal } from 'lucide-react';

export const RobotMascot: React.FC = () => {
  const [activeTask, setActiveTask] = useState<string>(
    'Scanning DPDP Act 2023 & CERT-In Statutory Matrix...'
  );
  const [isScanning, setIsScanning] = useState<boolean>(true);

  const TASKS = [
    'Scanning DPDP Act 2023 & CERT-In Statutory Matrix...',
    'Evaluating 6-Hour CERT-In Incident Notification Protocol...',
    'Audit: Cross-Border AWS Singapore Storage Non-Compliance...',
    'Verifying UIDAI Aadhaar Vault & SPDI Rules 2009...',
    'Calculating Maximum Schedule 1 Penalty Exposure (₹250 Cr)...',
  ];

  const handleInteract = () => {
    setIsScanning(true);
    const nextTask = TASKS[Math.floor(Math.random() * TASKS.length)];
    setActiveTask(nextTask);
    setTimeout(() => setIsScanning(false), 2500);
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="relative z-10 p-5 md:p-6 mb-8 rounded-2xl glass-panel bg-gradient-to-r from-black via-zinc-950 to-amber-950/40 border border-amber-500/40 shadow-glow-gold flex flex-col md:flex-row items-center justify-between gap-6"
    >
      {/* Robot Mascot 3D SVG & Scanner Projection */}
      <div className="flex items-center gap-5">
        <div
          onClick={handleInteract}
          className="relative w-28 h-28 md:w-32 md:h-32 shrink-0 cursor-pointer group"
          title="Click DPDP Robot Assistant to execute real-time statutory scan"
        >
          {/* Pulsing Aura */}
          <div className="absolute inset-0 rounded-full bg-amber-500/20 blur-xl group-hover:bg-amber-400/40 transition-all animate-pulse" />

          {/* Rotating Holographic Radar Ring */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-[-6px] rounded-full border border-dashed border-amber-400/60"
          />

          {/* Robot Body SVG */}
          <div className="relative w-full h-full rounded-2xl bg-black border-2 border-amber-400/60 p-2 flex items-center justify-center shadow-glow-gold group-hover:border-amber-300 transition-all overflow-hidden">
            <svg
              viewBox="0 0 100 100"
              className="w-full h-full transform group-hover:scale-105 transition-transform"
            >
              {/* Antenna */}
              <line x1="50" y1="12" x2="50" y2="24" stroke="#FBBF24" strokeWidth="3" strokeLinecap="round" />
              <circle cx="50" cy="10" r="4" fill="#F59E0B" className="animate-ping" />

              {/* Ears / Side Nodes */}
              <rect x="18" y="34" width="8" height="14" rx="3" fill="#B45309" />
              <rect x="74" y="34" width="8" height="14" rx="3" fill="#B45309" />

              {/* Head Shell */}
              <rect x="24" y="24" width="52" height="38" rx="10" fill="#18181b" stroke="#FBBF24" strokeWidth="2.5" />

              {/* Glowing Visor */}
              <rect x="30" y="32" width="40" height="18" rx="6" fill="#000000" stroke="#F59E0B" strokeWidth="1.5" />

              {/* Animated Laser Scanning Beam */}
              <motion.line
                x1="32"
                y1="41"
                x2="68"
                y2="41"
                stroke="#FDE047"
                strokeWidth="3"
                animate={{ y: [-4, 4, -4] }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
              />

              {/* Robot Eyes */}
              <circle cx="40" cy="41" r="3.5" fill="#FACC15" />
              <circle cx="60" cy="41" r="3.5" fill="#FACC15" />

              {/* Mouth / Speaker Grille */}
              <line x1="40" y1="53" x2="60" y2="53" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" />
              <line x1="44" y1="56" x2="56" y2="56" stroke="#B45309" strokeWidth="1.5" strokeLinecap="round" />

              {/* Neck */}
              <rect x="42" y="62" width="16" height="6" fill="#78350F" />

              {/* Chest Plate */}
              <path d="M 28 68 L 72 68 L 66 94 L 34 94 Z" fill="#09090b" stroke="#F59E0B" strokeWidth="2" />

              {/* Chest Core Reactor */}
              <circle cx="50" cy="80" r="6" fill="#FACC15" className="animate-pulse" />
              <circle cx="50" cy="80" r="9" fill="none" stroke="#F59E0B" strokeWidth="1.5" />
            </svg>
          </div>
        </div>

        {/* Robot Speech & Live Action */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/40 text-[11px] font-bold font-robot uppercase tracking-wider flex items-center gap-1.5 shadow-sm">
              <Bot className="w-3.5 h-3.5 text-amber-400" />
              <span>DPDP Cyber Bot v2.0</span>
            </span>
            <span className="text-[11px] font-mono text-zinc-400">Status: Active Scan</span>
          </div>

          <h3 className="text-base md:text-lg font-bold text-white font-heading leading-tight flex items-center gap-2">
            <span>Automated Statutory DPDP Command Bot</span>
          </h3>

          {/* Interactive Speech Box */}
          <div className="p-3 rounded-xl bg-black/80 border border-amber-500/30 text-xs font-mono text-amber-200 flex items-center gap-2 shadow-inner">
            <Terminal className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="truncate">{activeTask}</span>
          </div>
        </div>
      </div>

      {/* Right Robot Actions & Click Trigger */}
      <div className="flex flex-col sm:flex-row md:flex-col items-end gap-3 shrink-0">
        <button
          onClick={handleInteract}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-400 text-black font-robot font-bold text-xs shadow-glow-gold hover:bg-amber-300 active:scale-[0.98] transition-all cursor-pointer"
        >
          <Scan className="w-4 h-4" />
          <span>Trigger Bot Audit Scan</span>
        </button>

        <div className="flex items-center gap-2 text-[11px] font-mono text-zinc-400">
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
          <span>100% Grounded Statutory Engine</span>
        </div>
      </div>
    </motion.div>
  );
};
