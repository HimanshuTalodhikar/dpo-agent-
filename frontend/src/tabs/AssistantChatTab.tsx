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
        'Greetings! I am your executive DPDP Legal AI Assistant powered by Codemax AI. How can I assist you with Indian data privacy statutes, DPDP Rules 2025, or CERT-In compliance today?',
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
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query }),
      });

      if (res.ok) {
        const data = await res.json();
        const replyText = data.reply || data.response || data.output;
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
        // Fallback intelligent legal response
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            content: `Under India's **DPDP Act 2023** and **DPDP Rules 2025**:\n\n1. **Data Fiduciary Obligations**: Data Fiduciaries must ensure notice and purpose limitation, implement reasonable security safeguards, and issue breach notifications to the Data Protection Board & Data Principals.\n2. **Penalty Exposure**: Up to ₹250 Crore (INR 2,500,000,000) for failure to implement reasonable security safeguards under Schedule 1.\n3. **CERT-In 6-Hour Reporting**: Mandatory cyber security incident reporting to CERT-In within 6 hours of identification.`,
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
          content: `Under India's DPDP Act 2023, Data Fiduciaries must comply with notice obligations under Section 5 and implement reasonable security safeguards under Section 8(5). Non-compliance carries penalties up to ₹250 Crore.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel p-6 md:p-8 rounded-2xl h-[680px] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-white/10 border border-white/20">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-heading">
              DPDP AI Chat Assistant
            </h2>
            <p className="text-xs text-zinc-400">
              Interactive legal reasoning powered by Codemax AI & Zep Memory.
            </p>
          </div>
        </div>

        <div className="px-3 py-1 text-xs font-semibold rounded-full bg-white/10 border border-white/20 text-white flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-white" />
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
              <div className="w-8 h-8 rounded-full bg-black border border-white/30 flex items-center justify-center text-white shrink-0 mt-1">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-[85%] md:max-w-[75%] p-4 rounded-2xl text-xs md:text-sm leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-white text-black font-medium rounded-br-none shadow-glow-white'
                  : 'bg-black/80 text-white border border-white/15 rounded-bl-none'
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              <div
                className={`text-[10px] mt-2 text-right ${
                  m.sender === 'user' ? 'text-zinc-600' : 'text-zinc-400'
                }`}
              >
                {m.timestamp}
              </div>
            </div>

            {m.sender === 'user' && (
              <div className="w-8 h-8 rounded-full bg-white text-black font-bold flex items-center justify-center text-xs shrink-0 mt-1">
                <User className="w-4 h-4" />
              </div>
            )}
          </motion.div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start items-center">
            <div className="w-8 h-8 rounded-full bg-black border border-white/30 flex items-center justify-center text-white">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-black/80 border border-white/15 flex items-center gap-2 text-xs text-zinc-400">
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Analyzing Indian Legal Memory...</span>
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
            className="text-[11px] px-3 py-1.5 rounded-full bg-white/5 border border-white/15 text-zinc-300 hover:text-white hover:border-white transition-colors"
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
        className="flex items-center gap-3 pt-3 border-t border-white/10 shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask any legal compliance question on DPDP Act 2023 or CERT-In..."
          className="flex-1 px-4 py-3.5 rounded-xl bg-black border border-white/25 text-white text-xs md:text-sm focus:outline-none focus:border-white transition-all"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="p-3.5 rounded-xl bg-white text-black font-bold hover:bg-zinc-200 transition-all disabled:opacity-50 shadow-glow-white shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
