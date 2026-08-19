import React from 'react';
import { motion } from 'framer-motion';
import { TabType } from '../types';
import {
  Gavel,
  Wrench,
  Scale,
  Database,
  FilePlus,
  MessageSquare,
  Plug,
} from 'lucide-react';

interface TabNavProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
}

const TABS: { id: TabType; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: 'risk', label: 'Legal Risk Analyzer', icon: Gavel },
  { id: 'remediation', label: '30-Day Remediation Plan', icon: Wrench },
  { id: 'audit', label: 'Legal Audit Suite', icon: Scale },
  { id: 'search', label: 'Statutory Knowledge Base', icon: Database },
  { id: 'ingest', label: 'Ingest Statutory Acts', icon: FilePlus },
  { id: 'chat', label: 'DPDP Assistant Chat', icon: MessageSquare },
  { id: 'mcp', label: 'Claude Desktop / MCP', icon: Plug },
];

export const TabNav: React.FC<TabNavProps> = ({ activeTab, onSelectTab }) => {
  return (
    <nav className="relative z-10 flex items-center gap-2 p-1.5 mb-8 glass-panel rounded-2xl overflow-x-auto no-scrollbar">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onSelectTab(tab.id)}
            className={`relative flex items-center gap-2 px-4 py-2.5 rounded-xl font-heading text-sm font-semibold whitespace-nowrap transition-colors z-10 ${
              isActive ? 'text-black' : 'text-zinc-400 hover:text-white'
            }`}
          >
            {isActive && (
              <motion.div
                layoutId="activeTabPill"
                className="absolute inset-0 bg-white rounded-xl shadow-glow-white -z-10"
                transition={{ type: 'spring', stiffness: 380, damping: 30 }}
              />
            )}
            <Icon className={`w-4 h-4 ${isActive ? 'text-black' : 'text-zinc-400'}`} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
