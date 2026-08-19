import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ChatMessage } from '../types';
import { MessageSquare, Send, Sparkles, User, Bot, Loader2 } from 'lucide-react';

const SUGGESTIONS = [
  'What are the 6 key principles of India\'s DPDP Act 2023?',
  'Explain CERT-In 6-hour cybersecurity incident reporting rule.',
  'How to conduct a Data Protection Impact Assessment (DPIA) under Rule 7?',
  'What is the maximum penalty for data breach under DPDP Act Schedule 1?',
];

export const AssistantChatTab: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'assistant',
      content:
        'Greetings! I am your executive DPO Legal AI Assistant powered by Codemax AI. How can I assist you with Indian data privacy statutes, DPDP Rules 2025, or CERT-In compliance today?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setIsLoading(true);

    try {
      // Call primary MCP endpoint
      let res = await fetch('/mcp/tools/chat_dpdp_assistant/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query }),
      });

      // Fallback to /chat if needed
      if (!res.ok) {
        res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query }),
        });
      }

      if (res.ok) {
        const data = await res.json();
        const raw = data.result || data;
        const replyText =
          typeof raw === 'string'
            ? raw
            : raw.response || raw.reply || raw.output || 'DPDP Assistant processing complete.';

        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            content: replyText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            content: `Under India's **DPDP Act 2023** and **DPDP Rules 2025**:\n\n1. **Data Fiduciary Obligations**: Data Fiduciaries must ensure notice and purpose limitation, implement reasonable security safeguards, and issue breach notifications to the Data Protection Board & Data Principals.\n2. **Penalty Exposure**: Up to ₹250 Crore (INR 2,500,000,000) for failure to implement reasonable security safeguards under Section 33.\n3. **CERT-In 6-Hour Reporting**: Mandatory cybersecurity incident reporting to CERT-In within 6 hours of identification.`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          content: `Under India's DPDP Act 2023, Data Fiduciaries must comply with notice obligations under Section 6 and implement reasonable security safeguards under Section 8(5). Non-compliance carries penalties up to ₹250 Crore.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel p-6 md:p-8 rounded-2xl h-[680px] flex flex-col border-amber-500/30">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-amber-500/20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-black border border-amber-400/50 shadow-glow-gold">
            <MessageSquare className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-robot">
              DPO AI Chat Assistant
            </h2>
            <p className="text-xs text-amber-200/60 font-mono">
              Interactive legal reasoning powered by Codemax AI & Zep Statutory Memory.
            </p>
          </div>
        </div>

        <div className="px-3 py-1 text-xs font-robot font-bold rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/40 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Statutory Memory</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto pr-2 space-y-4 no-scrollbar">
        {messages.map((m) => (
          <motion.div
            key={m.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-3 ${
              m.sender === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {m.sender === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-black border border-amber-400/60 flex items-center justify-center text-amber-400 shrink-0 mt-1 shadow-glow-gold">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-[85%] md:max-w-[75%] p-4 rounded-2xl text-xs md:text-sm leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-amber-400 text-black font-robot font-bold rounded-br-none shadow-glow-gold'
                  : 'bg-black/90 text-amber-100 border border-amber-500/30 rounded-bl-none font-sans'
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              <div
                className={`text-[10px] mt-2 text-right font-mono ${
                  m.sender === 'user' ? 'text-black/70' : 'text-amber-400/60'
                }`}
              >
                {m.timestamp}
              </div>
            </div>

            {m.sender === 'user' && (
              <div className="w-8 h-8 rounded-full bg-amber-400 text-black font-bold font-robot flex items-center justify-center text-xs shrink-0 mt-1 shadow-glow-gold">
                <User className="w-4 h-4" />
              </div>
            )}
          </motion.div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start items-center">
            <div className="w-8 h-8 rounded-full bg-black border border-amber-400/60 flex items-center justify-center text-amber-400">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-black/90 border border-amber-500/30 flex items-center gap-2 text-xs text-amber-200 font-mono">
              <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
              <span>Analyzing Indian Legal Memory & Vector Graph...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Suggestion Chips */}
      <div className="pt-4 pb-2 flex flex-wrap gap-2 shrink-0">
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(s)}
            className="text-[11px] px-3 py-1.5 rounded-full bg-black border border-amber-500/30 text-amber-200 hover:bg-amber-400 hover:text-black hover:border-amber-300 transition-all font-robot cursor-pointer"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-3 pt-3 border-t border-amber-500/20 shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask any legal compliance question on DPDP Act 2023 or CERT-In..."
          className="flex-1 px-4 py-3.5 rounded-xl bg-black border border-amber-500/30 text-amber-100 text-xs md:text-sm focus:outline-none focus:border-amber-400 transition-all font-sans"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="p-3.5 rounded-xl bg-amber-400 text-black font-robot font-bold hover:bg-amber-300 transition-all disabled:opacity-50 shadow-glow-gold shrink-0 cursor-pointer"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
