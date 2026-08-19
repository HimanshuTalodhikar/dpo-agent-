import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plug, Copy, Check, ExternalLink, Terminal, Shield, Sparkles } from 'lucide-react';

export const MCPConnectTab: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const mcpConfigJson = JSON.stringify(
    {
      mcpServers: {
        'dpdp-ai-agent': {
          command: 'uv',
          args: ['run', 'src/main.py'],
          env: {
            ZEP_API_KEY: 'your-zep-api-key',
            PRIMARY_JURISDICTION: 'IN',
          },
        },
      },
    },
    null,
    2
  );

  const handleCopy = () => {
    navigator.clipboard.writeText(mcpConfigJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel p-6 md:p-8 rounded-2xl max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b border-white/10">
        <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
          <Plug className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white font-heading">
            Connect Claude Desktop & External MCP Clients
          </h2>
          <p className="text-xs text-zinc-400">
            Integrate Model Context Protocol (MCP) tool capabilities directly into Claude Desktop or Cursor.
          </p>
        </div>
      </div>

      {/* Endpoints Table */}
      <div className="p-4 rounded-xl bg-black border border-white/15 space-y-3">
        <h4 className="text-xs font-bold text-white font-heading flex items-center gap-2">
          <Terminal className="w-4 h-4 text-white" />
          <span>Active AWS Load Balancer MCP Server Endpoints</span>
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 font-mono">
            <span className="text-zinc-500 block">SSE Transport Endpoint:</span>
            <strong className="text-white">https://www.digiprotect.ai/sse</strong>
          </div>

          <div className="p-3 rounded-lg bg-white/5 border border-white/10 font-mono">
            <span className="text-zinc-500 block">Tool Registry Endpoint:</span>
            <strong className="text-white">https://www.digiprotect.ai/mcp/tools</strong>
          </div>
        </div>
      </div>

      {/* Config Snippet */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-white">
            Claude Desktop Configuration File (<code className="text-zinc-400">claude_desktop_config.json</code>):
          </label>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-medium transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy JSON</span>
              </>
            )}
          </button>
        </div>

        <pre className="p-4 rounded-xl bg-black border border-white/20 text-xs font-mono text-white leading-relaxed overflow-x-auto">
          {mcpConfigJson}
        </pre>
      </div>

      {/* Tools List */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-white font-heading">
          Exposed Model Context Protocol (MCP) Tools
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            { name: 'analyze_legal_risk', desc: 'Evaluates regulatory exposure & priority rank under Indian law.' },
            { name: 'generate_remediation', desc: 'Computes 30-day step timeline with cost estimates in USD.' },
            { name: 'run_legal_audit', desc: 'Executes comprehensive audit suite & outputs recommendation.' },
            { name: 'get_agent_status', desc: 'Queries system health and indexed vector store statistics.' },
          ].map((t) => (
            <div key={t.name} className="p-3.5 rounded-xl bg-white/5 border border-white/15">
              <div className="font-mono font-bold text-white mb-1">{t.name}</div>
              <div className="text-zinc-400">{t.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
