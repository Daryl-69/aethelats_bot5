import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, Send, RefreshCw, User, ChevronRight, Target, TrendingUp, TrendingDown, Zap } from 'lucide-react';
import { API_URL } from './constants';

const SUGGESTED_QUESTIONS = [
  "What salary should I expect for my role and experience?",
  "Which skills should I learn next to reach the next level?",
  "How do I transition from a service company to a product company?",
  "What are the top companies hiring for my role in India right now?",
  "Give me a 3-month action plan to close my skill gaps.",
  "How do I negotiate a higher salary offer?",
];

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
        <Sparkles className="w-4 h-4 text-indigo-300" />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm"
        style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)' }}>
        <div className="flex gap-1.5 items-center h-5">
          <span className="w-2 h-2 rounded-full bg-indigo-400/60 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 rounded-full bg-indigo-400/60 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 rounded-full bg-indigo-400/60 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex items-end gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser
          ? 'bg-white/10 border border-white/15'
          : 'bg-indigo-500/20 border border-indigo-500/30'
      }`}>
        {isUser
          ? <User className="w-4 h-4 text-white/70" />
          : <Sparkles className="w-4 h-4 text-indigo-300" />
        }
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
        isUser
          ? 'rounded-br-sm bg-white/10 border border-white/10 text-white'
          : 'rounded-bl-sm text-white/90'
      }`}
        style={!isUser ? {
          background: 'rgba(99,102,241,0.08)',
          border: '1px solid rgba(99,102,241,0.15)'
        } : {}}>
        {msg.content}
      </div>
    </div>
  );
}

export default function AiCoachView({ s }) {
  const result = s?.result;
  const hasResult = !!result;

  // Extract resume context
  const resumeSkills = result?.structured_data?.technical_skills || [];
  const missingSkills = (result?.gaps || []).map(g => g.gap).filter(Boolean);
  const targetRole = s?.jobRole || '';
  const fairaiScore = result?.fit_score ?? null;
  const legacyScore = result?.counterfactual?.legacy_ats_score ?? null;
  const experienceYears = result?.structured_data?.work_experience_summary?.total_years ?? null;

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [welcomed, setWelcomed] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Send a welcome message the first time the coach opens with a result
  useEffect(() => {
    if (hasResult && !welcomed && messages.length === 0) {
      setWelcomed(true);
      const greeting = buildGreeting(fairaiScore, targetRole, missingSkills);
      setMessages([{ role: 'assistant', content: greeting }]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasResult]);

  function buildGreeting(score, role, gaps) {
    if (!score && !role) {
      return "Hi! I'm your Aethel AI Career Coach. I'm powered by real data from 97,000 Indian job postings. Ask me anything about salaries, skills, career paths, or interview prep!";
    }
    const scoreMsg = score
      ? `Your resume scored **${score}/100**${role ? ` for ${role}` : ''}. `
      : '';
    const gapMsg = gaps.length > 0
      ? `I can see you're missing ${gaps.slice(0, 3).join(', ')}${gaps.length > 3 ? ' and more' : ''}. `
      : '';
    return `Hi! I've reviewed your resume analysis. ${scoreMsg}${gapMsg}\n\nI'm backed by real data from 97,000 Indian job postings — I can tell you exact salary ranges, which skills to learn next, and how to close your gaps. What would you like to know?`;
  }

  async function sendMessage(text) {
    const userMsg = text.trim();
    if (!userMsg || loading) return;

    const newHistory = [...messages, { role: 'user', content: userMsg }];
    setMessages(newHistory);
    setInput('');
    setLoading(true);

    try {
      const API_BASE = API_URL || 'https://daryllll-gyufuyf.hf.space';
      const res = await fetch(`${API_BASE}/coach/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          history: messages.slice(-10),  // last 10 turns
          resume_skills: resumeSkills,
          missing_skills: missingSkills,
          target_role: targetRole,
          fairai_score: fairaiScore,
          legacy_score: legacyScore,
          experience_years: experienceYears,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I ran into an issue: ${err.message}. Please try again in a moment.`
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleReset() {
    setMessages([]);
    setWelcomed(false);
    setTimeout(() => {
      const greeting = buildGreeting(fairaiScore, targetRole, missingSkills);
      setMessages([{ role: 'assistant', content: greeting }]);
    }, 100);
  }

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-3.5rem)] overflow-hidden">

      {/* ── LEFT PANEL: Resume Context ── */}
      <aside className="w-full lg:w-72 shrink-0 border-b lg:border-b-0 lg:border-r border-white/[0.06] overflow-y-auto p-5 space-y-4"
        style={{ background: 'rgba(0,0,0,0.3)' }}>

        {/* Header */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">AI Career Coach</div>
            <div className="text-[10px] text-white/40 uppercase tracking-wider">Powered by 97k job postings</div>
          </div>
        </div>

        {hasResult ? (
          <>
            {/* Score card */}
            {fairaiScore !== null && (
              <div className="rounded-xl p-4 border border-indigo-500/20"
                style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.08))' }}>
                <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-400/70 mb-1">Your FairAI Score</div>
                <div className="text-4xl font-black text-white">{fairaiScore}<span className="text-lg text-white/40">/100</span></div>
                {targetRole && <div className="text-xs text-white/50 mt-1">for {targetRole}</div>}
              </div>
            )}

            {/* Skills you have */}
            {resumeSkills.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-[11px] font-bold uppercase tracking-wider text-white/50">Detected Skills</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {resumeSkills.slice(0, 12).map((skill, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      {skill}
                    </span>
                  ))}
                  {resumeSkills.length > 12 && (
                    <span className="px-2 py-0.5 rounded-md text-[11px] text-white/30 border border-white/10">
                      +{resumeSkills.length - 12} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Skill gaps */}
            {missingSkills.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
                  <span className="text-[11px] font-bold uppercase tracking-wider text-white/50">Skill Gaps</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {missingSkills.slice(0, 8).map((skill, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="rounded-xl p-4 border border-white/[0.06] text-sm text-white/40 leading-relaxed">
            <Zap className="w-5 h-5 text-indigo-400/50 mb-2" />
            No resume analyzed yet. Analyze a resume first to get personalized coaching — or ask me any general career question!
          </div>
        )}

        {/* Suggested questions */}
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wider text-white/30 mb-2">Try asking</div>
          <div className="space-y-1.5">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button key={i}
                onClick={() => sendMessage(q)}
                disabled={loading}
                className="w-full text-left text-xs text-white/50 hover:text-white/80 px-3 py-2 rounded-lg hover:bg-white/[0.04] border border-transparent hover:border-white/[0.06] transition-all flex items-start gap-2 group disabled:opacity-40">
                <ChevronRight className="w-3 h-3 mt-0.5 shrink-0 text-indigo-500/50 group-hover:text-indigo-400 transition-colors" />
                <span>{q}</span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* ── RIGHT PANEL: Chat ── */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">

        {/* Chat header */}
        <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-white/[0.06]"
          style={{ background: 'rgba(0,0,0,0.3)' }}>
          <div>
            <div className="text-sm font-semibold text-white">Career Q&A</div>
            <div className="text-xs text-white/40">Backed by real Indian job market data</div>
          </div>
          <button onClick={handleReset} title="Reset conversation"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/40 hover:text-white/70 hover:bg-white/[0.04] border border-white/[0.06] transition-all">
            <RefreshCw className="w-3.5 h-3.5" /> Reset
          </button>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-indigo-400" />
              </div>
              <div>
                <div className="text-lg font-bold text-white mb-1">Your AI Career Coach</div>
                <div className="text-sm text-white/40 max-w-sm">
                  Ask anything about salaries, skills to learn, career transitions, or interview prep — all backed by 97,000 real Indian job postings.
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <Message key={i} msg={msg} />
          ))}

          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="shrink-0 px-6 py-4 border-t border-white/[0.06]"
          style={{ background: 'rgba(0,0,0,0.3)' }}>
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about salaries, skills, career paths, interviews..."
                rows={1}
                disabled={loading}
                className="w-full resize-none rounded-xl px-4 py-3 text-sm text-white placeholder-white/30
                  bg-white/[0.04] border border-white/[0.08] focus:border-indigo-500/40
                  focus:outline-none focus:ring-0 transition-all leading-relaxed
                  disabled:opacity-50 max-h-32"
                style={{ scrollbarWidth: 'thin' }}
                onInput={e => {
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
                }}
              />
            </div>
            <button
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
              className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-all
                disabled:opacity-30 disabled:cursor-not-allowed
                bg-indigo-500/20 border border-indigo-500/30 text-indigo-300
                hover:bg-indigo-500/30 hover:border-indigo-500/50 active:scale-95"
            >
              {loading
                ? <RefreshCw className="w-4 h-4 animate-spin" />
                : <Send className="w-4 h-4" />
              }
            </button>
          </div>
          <div className="text-[10px] text-white/20 mt-2 text-center">
            Press Enter to send · Shift+Enter for new line · Backed by 97k real Indian job postings
          </div>
        </div>
      </div>
    </div>
  );
}
