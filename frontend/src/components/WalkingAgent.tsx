import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Sparkles, Shield, Zap, Terminal, X } from 'lucide-react';

interface WalkingAgentProps {
  onTriggerScan?: () => void;
}

const PATROL_MESSAGES = [
  '🔍 DPO Cyberbot patrolling website for DPDP Act 2023 compliance...',
  '⚡ Inspecting CERT-In 6-Hour Incident Notification readiness...',
  '🛡️ Scanning cross-border data transfer logs to AWS Singapore...',
  '🔒 Verifying Aadhaar UIDAI mask vault & SPDI Rules 2009...',
  '⚖️ DPO Agent Vigilance: 100% Grounded Statutory Protection!',
  '🤖 System nominal. 250 Cr Schedule 1 Penalty Matrix active.',
];

export const WalkingAgent: React.FC<WalkingAgentProps> = ({ onTriggerScan }) => {
  const [posX, setPosX] = useState<number>(80);
  const [direction, setDirection] = useState<1 | -1>(1); // 1 = right, -1 = left
  const [messageIdx, setMessageIdx] = useState<number>(0);
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const [isInteracting, setIsInteracting] = useState<boolean>(false);
  const [stepAngle, setStepAngle] = useState<number>(0);

  // Autonomous walking movement loop
  useEffect(() => {
    const interval = setInterval(() => {
      if (isHovered || isInteracting) return;

      setPosX((prevX) => {
        const speed = 1.6;
        let nextX = prevX + direction * speed;
        const screenMax = window.innerWidth - 120;

        // Turn around at screen edges
        if (nextX > screenMax) {
          setDirection(-1);
          return screenMax;
        } else if (nextX < 40) {
          setDirection(1);
          return 40;
        }
        return nextX;
      });

      // Animate leg swing
      setStepAngle((prev) => (prev + 0.3) % (Math.PI * 2));
    }, 30);

    return () => clearInterval(interval);
  }, [direction, isHovered, isInteracting]);

  // Periodic message update loop
  useEffect(() => {
    const msgInterval = setInterval(() => {
      setMessageIdx((prev) => (prev + 1) % PATROL_MESSAGES.length);
    }, 6000);

    return () => clearInterval(msgInterval);
  }, []);

  const handleBotClick = () => {
    setIsInteracting(true);
    setMessageIdx((prev) => (prev + 1) % PATROL_MESSAGES.length);
    if (onTriggerScan) onTriggerScan();
    setTimeout(() => setIsInteracting(false), 3000);
  };

  const legSwing1 = Math.sin(stepAngle) * 20;
  const legSwing2 = -Math.sin(stepAngle) * 20;

  return (
    <div
      className="fixed bottom-4 z-40 pointer-events-none transition-transform duration-75 ease-linear select-none"
      style={{ left: `${posX}px` }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="relative group pointer-events-auto">
        {/* Floating Patrol Speech Bubble */}
        <AnimatePresence mode="wait">
          <motion.div
            key={messageIdx}
            initial={{ opacity: 0, y: 10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            className="absolute bottom-28 left-1/2 -translate-x-1/2 w-64 p-3 rounded-2xl bg-black/90 border border-amber-400/60 shadow-glow-gold text-amber-200 text-xs font-mono backdrop-blur-md space-y-1"
          >
            <div className="flex items-center justify-between border-b border-amber-500/20 pb-1 text-[10px] text-amber-400 font-robot">
              <span className="flex items-center gap-1">
                <Bot className="w-3 h-3 text-amber-400" />
                <span>DPO PATROL BOT</span>
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
            </div>
            <p className="text-[11px] leading-tight text-white font-sans font-medium">
              {PATROL_MESSAGES[messageIdx]}
            </p>
            {/* Pointer Arrow */}
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-3 h-3 bg-black border-r border-b border-amber-400/60 rotate-45" />
          </motion.div>
        </AnimatePresence>

        {/* Walking Robot Mascot SVG */}
        <motion.div
          onClick={handleBotClick}
          whileHover={{ scale: 1.15 }}
          whileTap={{ scale: 0.95 }}
          className="relative w-20 h-24 cursor-pointer"
          style={{ transform: direction === -1 ? 'scaleX(-1)' : 'scaleX(1)' }}
        >
          {/* Ground Shadow */}
          <div className="absolute bottom-0 left-2 right-2 h-2 rounded-full bg-amber-400/30 blur-sm animate-pulse" />

          {/* Downward Scanner Beam Projection */}
          <motion.div
            animate={{ opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="absolute top-12 left-1/2 -translate-x-1/2 w-16 h-12 bg-gradient-to-b from-amber-400/30 to-transparent clip-triangle pointer-events-none"
            style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}
          />

          <svg viewBox="0 0 100 120" className="w-full h-full drop-shadow-glow-gold">
            {/* Antenna */}
            <line x1="50" y1="8" x2="50" y2="20" stroke="#FBBF24" strokeWidth="3" strokeLinecap="round" />
            <circle cx="50" cy="6" r="4" fill="#FACC15" className="animate-ping" />

            {/* Robot Head */}
            <rect x="24" y="20" width="52" height="34" rx="9" fill="#18181b" stroke="#F59E0B" strokeWidth="2.5" />

            {/* Glowing Visor */}
            <rect x="30" y="28" width="40" height="16" rx="5" fill="#000000" stroke="#FBBF24" strokeWidth="1.5" />
            <circle cx="42" cy="36" r="3.5" fill="#FACC15" />
            <circle cx="58" cy="36" r="3.5" fill="#FACC15" />

            {/* Visor Laser Scan Bar */}
            <motion.line
              x1="32"
              y1="36"
              x2="68"
              y2="36"
              stroke="#FDE047"
              strokeWidth="2.5"
              animate={{ y: [-3, 3, -3] }}
              transition={{ duration: 0.8, repeat: Infinity }}
            />

            {/* Neck */}
            <rect x="42" y="54" width="16" height="5" fill="#78350F" />

            {/* Torso */}
            <path d="M 28 59 L 72 59 L 66 84 L 34 84 Z" fill="#09090b" stroke="#F59E0B" strokeWidth="2.5" />
            <circle cx="50" cy="72" r="5" fill="#FACC15" className="animate-pulse" />

            {/* Animated Walking Legs */}
            <g transform={`rotate(${legSwing1}, 40, 84)`}>
              <rect x="36" y="84" width="10" height="24" rx="4" fill="#18181b" stroke="#FBBF24" strokeWidth="1.5" />
              <rect x="34" y="104" width="14" height="6" rx="2" fill="#F59E0B" />
            </g>

            <g transform={`rotate(${legSwing2}, 60, 84)`}>
              <rect x="54" y="84" width="10" height="24" rx="4" fill="#18181b" stroke="#FBBF24" strokeWidth="1.5" />
              <rect x="52" y="104" width="14" height="6" rx="2" fill="#F59E0B" />
            </g>
          </svg>
        </motion.div>
      </div>
    </div>
  );
};
