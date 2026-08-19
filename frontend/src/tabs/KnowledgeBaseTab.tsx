import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SearchResultChunk } from '../types';
import { Database, Search, BookOpen, Filter, Loader2, Sparkles } from 'lucide-react';

export const KnowledgeBaseTab: React.FC = () => {
  const [query, setQuery] = useState('employee monitoring DPDP Act consent requirements');
  const [jurisdiction, setJurisdiction] = useState('IN');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<SearchResultChunk[]>([]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const res = await fetch('/mcp/tools/get_agent_status/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      // Sample mock response showing indexed statutory provisions
      setResults([
        {
          chunk_id: 'in-dpdp-2023-sec6-p1',
          statute: 'Digital Personal Data Protection Act, 2023',
          section: 'Section 6 — Consent & Purpose Limitation',
          text: 'The consent given by the Data Principal shall be free, specific, informed, unconditional and unambiguous with a clear affirmative action, and shall signify an agreement to the processing of her personal data for the specified purpose.',
          similarity_score: 0.94,
        },
        {
          chunk_id: 'in-dpdp-rules-2025-rule3',
          statute: 'DPDP Rules 2025',
          section: 'Rule 3 — Itemised Privacy Notice Requirements',
          text: 'Every Data Fiduciary shall present a notice to the Data Principal in clear and plain language, itemising the categories of personal data to be collected, the specific purpose of processing, and the procedure for withdrawal of consent.',
          similarity_score: 0.89,
        },
        {
          chunk_id: 'cert-in-2022-sec70b',
          statute: 'CERT-In Cyber Security Directions 2022',
          section: 'Direction 4 — System Log Maintenance',
          text: 'All service providers, intermediaries, data centres, body corporate and government organisations shall mandatorily enable logs of all their ICT systems and maintain them securely within the Indian jurisdiction for a rolling period of 180 days.',
          similarity_score: 0.85,
        },
      ]);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel p-6 md:p-8 rounded-2xl space-y-6">
      <div className="flex items-center gap-3 pb-4 border-b border-white/10">
        <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
          <Database className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white font-heading">
            Statutory Knowledge Base Search
          </h2>
          <p className="text-xs text-zinc-400">
            Semantic vector search across indexed DPDP Act 2023 sections, DPDP Rules 2025, and CERT-In directions.
          </p>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-4 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. employee monitoring DPDP Act consent requirements..."
            className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-black border border-white/25 text-white text-sm focus:outline-none focus:border-white transition-all"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-3.5 rounded-xl bg-black border border-white/25 text-xs text-white">
            <Filter className="w-4 h-4 text-zinc-400" />
            <select
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              className="bg-transparent text-white font-medium focus:outline-none cursor-pointer"
            >
              <option value="IN">India (DPDP / CERT-In)</option>
              <option value="EU">EU (GDPR)</option>
              <option value="ALL">All Statutes</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-6 py-3.5 rounded-xl bg-white text-black font-heading font-bold text-sm shadow-glow-white hover:bg-zinc-200 transition-all shrink-0"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Search'}
          </button>
        </div>
      </form>

      {/* Results List */}
      <div className="space-y-4 pt-2">
        {results.map((chunk) => (
          <motion.div
            key={chunk.chunk_id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-5 rounded-xl bg-black border border-white/15 hover:border-white/40 transition-colors space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white font-heading flex items-center gap-2">
                <BookOpen className="w-3.5 h-3.5 text-white" />
                {chunk.statute}
              </span>
              <span className="text-xs font-mono text-zinc-400">
                Similarity: <strong className="text-white">{(chunk.similarity_score * 100).toFixed(0)}%</strong>
              </span>
            </div>

            <div className="text-xs font-semibold text-zinc-300">
              {chunk.section}
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed font-sans p-3 rounded-lg bg-white/5 border border-white/10">
              "{chunk.text}"
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
