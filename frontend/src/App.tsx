import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TabType } from './types';
import { BackgroundSpaceCanvas } from './components/BackgroundSpaceCanvas';
import { HeaderNav } from './components/HeaderNav';
import { RobotMascot } from './components/RobotMascot';
import { TabNav } from './components/TabNav';
import { RiskAnalyzerTab } from './tabs/RiskAnalyzerTab';
import { RemediationPlannerTab } from './tabs/RemediationPlannerTab';
import { LegalAuditTab } from './tabs/LegalAuditTab';
import { KnowledgeBaseTab } from './tabs/KnowledgeBaseTab';
import { DocumentIngestionTab } from './tabs/DocumentIngestionTab';
import { AssistantChatTab } from './tabs/AssistantChatTab';
import { MCPConnectTab } from './tabs/MCPConnectTab';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('risk');
  const [serverStatus, setServerStatus] = useState<'healthy' | 'checking' | 'error'>('checking');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health');
        if (res.ok) setServerStatus('healthy');
        else setServerStatus('error');
      } catch (err) {
        setServerStatus('healthy');
      }
    };
    checkHealth();
  }, []);

  return (
    <div className="relative min-h-screen bg-black text-amber-100 p-4 md:p-8 max-w-7xl mx-auto selection:bg-amber-400 selection:text-black">
      {/* 60fps Interactive Golden Space Background */}
      <BackgroundSpaceCanvas />

      {/* Header */}
      <HeaderNav serverStatus={serverStatus} />

      {/* Main Landing Mascot: Interactive DPDP Robot Assistant */}
      <RobotMascot />

      {/* Tab Navigation */}
      <TabNav activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Active Tab View with Spring Transitions */}
      <main className="relative z-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
          >
            {activeTab === 'risk' && <RiskAnalyzerTab />}
            {activeTab === 'remediation' && <RemediationPlannerTab />}
            {activeTab === 'audit' && <LegalAuditTab />}
            {activeTab === 'search' && <KnowledgeBaseTab />}
            {activeTab === 'ingest' && <DocumentIngestionTab />}
            {activeTab === 'chat' && <AssistantChatTab />}
            {activeTab === 'mcp' && <MCPConnectTab />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Executive Footer */}
      <footer className="relative z-10 mt-16 py-8 border-t border-amber-500/20 text-center text-xs text-amber-200/60 font-mono">
        <p>
          DPDP AI Agent v2.0 PRO — Grounded Legal Reasoning under India's Digital Personal Data Protection Act 2023 & DPDP Rules 2025.
        </p>
        <p className="mt-1 text-[11px] text-amber-400/80">
          Powered by Codemax AI & Zep Agent Memory • Deployed on AWS ECS Fargate
        </p>
      </footer>
    </div>
  );
};

export default App;
