import React from 'react';
import { motion } from 'framer-motion';
import { TabType } from '../types';
import {
  Gavel,
  CalendarCheck,
  Scale,
  Search,
  FileCheck,
  MessageSquare,
  Plug,
} from 'lucide-react';

interface TabNavProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
}

const TABS: { id: TabType; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: 'risk', label: 'Risk Analyzer', icon: Gavel },
  { id: 'remediation', label: 'Remediation Plan', icon: CalendarCheck },
  { id: 'audit', label: 'Legal Audit Suite', icon: Scale },
  { id: 'search', label: 'Knowledge Graph', icon: Search },
  { id: 'ingest', label: 'Act & Rule Ingestor', icon: FileCheck },
  { id: 'chat', label: 'DPDP Assistant', icon: MessageSquare },
  { id: 'mcp', label: 'Claude / MCP Connect', icon: Plug },
];

export const TabNav: React.FC<TabNavProps> = ({ activeTab, onSelectTab }) => {
  return (
    <nav className="relative z-10 flex items-center justify-start md:justify-center gap-1.5 p-2 mb-8 glass-panel rounded-2xl overflow-x-auto border-amber-500/30">
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
  );
};
