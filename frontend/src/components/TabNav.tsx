import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { TabType } from '../types';
import {
  Home,
  Gavel,
  CalendarCheck,
  Scale,
  Search,
  FileCheck,
  MessageSquare,
  Plug,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface TabNavProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
}

const TABS: { id: TabType; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: 'landing', label: 'Home / Overview', icon: Home },
  { id: 'risk', label: 'Risk Analyzer', icon: Gavel },
  { id: 'remediation', label: 'Remediation Plan', icon: CalendarCheck },
  { id: 'audit', label: 'Legal Audit Suite', icon: Scale },
  { id: 'search', label: 'Knowledge Graph', icon: Search },
  { id: 'ingest', label: 'Act & Rule Ingestor', icon: FileCheck },
  { id: 'chat', label: 'DPDP Assistant', icon: MessageSquare },
  { id: 'mcp', label: 'Claude / MCP Connect', icon: Plug },
];

export const TabNav: React.FC<TabNavProps> = ({ activeTab, onSelectTab }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (!scrollRef.current) return;
    const scrollAmount = direction === 'left' ? -240 : 240;
    scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
  };

  return (
    <div className="relative z-20 mb-8 flex items-center gap-1.5">
      {/* Scroll Left Button */}
      <button
        onClick={() => scroll('left')}
        className="p-2.5 rounded-xl bg-black border border-amber-500/40 text-amber-400 hover:bg-amber-400 hover:text-black transition-all cursor-pointer shrink-0 shadow-glow-gold"
        title="Scroll Left to Home / Overview"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {/* Main Tab Bar Container */}
      <nav
        ref={scrollRef}
        className="flex-1 flex items-center justify-start gap-2 p-2 glass-panel rounded-2xl overflow-x-auto scroll-smooth no-scrollbar border-amber-500/30 touch-pan-x"
        style={{ WebkitOverflowScrolling: 'touch' }}
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`relative flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 shrink-0 font-robot cursor-pointer ${
                isActive
                  ? 'text-black font-extrabold'
                  : 'text-zinc-400 hover:text-amber-300 hover:bg-amber-400/10'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTabPill"
                  className="absolute inset-0 bg-amber-400 rounded-xl shadow-glow-gold"
                  transition={{ type: 'spring', stiffness: 450, damping: 35 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-2">
                <Icon className={`w-4 h-4 ${isActive ? 'text-black' : 'text-amber-400'}`} />
                <span>{tab.label}</span>
              </span>
            </button>
          );
        })}
      </nav>

      {/* Scroll Right Button */}
      <button
        onClick={() => scroll('right')}
        className="p-2.5 rounded-xl bg-black border border-amber-500/40 text-amber-400 hover:bg-amber-400 hover:text-black transition-all cursor-pointer shrink-0 shadow-glow-gold"
        title="Scroll Right to MCP / Connect"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
};
