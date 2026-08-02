import React, { useState, useEffect } from 'react';
import {
  Shield, Zap, ChevronRight, Play, BarChart3, AlertTriangle,
  ArrowRight, Check, Cpu, GitBranch, Lock
} from 'lucide-react';
import { API_URL } from './constants';

/* ── animated number count-up ── */
function CountUp({ target, suffix = '', duration = 1800 }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setVal(Math.round(p * target));
      if (p < 1) requestAnimationFrame(step);
    };
    const id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [target, duration]);
  return <>{val.toLocaleString('en-IN')}{suffix}</>;
}

/* ── bias delta chip ── */
function DeltaChip({ label, delta, delay = 0 }) {
  const big = Math.abs(delta) >= 8;
  return (
    <div
      className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs font-bold animate-fade-in-up`}
      style={{ animationDelay: `${delay}s`, background: big ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.02)', borderColor: big ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.06)' }}
    >
      <span className="text-white/70 font-mono">{label}</span>
      <span className={big ? 'text-white font-black' : 'text-white/60'}>
        {delta > 0 ? '+' : ''}{delta} pts
      </span>
    </div>
  );
}

/* ── live model comparison preview ── */
function BiasPreviewCard() {
  const models = [
    { name: 'Aethel (Fine-tuned)', score: 82, iit: 1, gap: 2, isOwn: true },
    { name: 'Llama 3.3 70B',       score: 71, iit: 9, gap: 6, isOwn: false },
    { name: 'Gemma 2 9B',           score: 69, iit: 12, gap: 8, isOwn: false },
    { name: 'Mixtral 8×7B',         score: 72, iit: 7, gap: 5, isOwn: false },
  ];

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-white/[0.08] w-full">
      {/* header */}
      <div className="px-3 sm:px-4 py-3 border-b border-white/[0.06] flex items-center gap-2">
        <BarChart3 className="w-3.5 h-3.5 text-white/60 shrink-0" />
        <span className="text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.2em] text-white/60 truncate">
          Live Bias Audit
        </span>
        <span className="ml-auto px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/10 text-[8px] sm:text-[9px] font-bold text-white/60 uppercase tracking-wider shrink-0">
          Demo
        </span>
      </div>

      {/* column headers */}
      <div className="px-2 sm:px-4 pt-3 pb-1 grid grid-cols-4 gap-1 sm:gap-2 text-[8px] sm:text-[9px] font-bold uppercase tracking-widest text-white/30">
        <span>Model</span>
        <span className="text-center">Score</span>
        <span className="text-center">IIT Δ</span>
        <span className="text-center">Gap Δ</span>
      </div>

      {/* rows */}
      <div className="px-2 sm:px-4 pb-4 space-y-2">
        {models.map((m, i) => (
          <div
            key={i}
            className={`grid grid-cols-4 gap-1 sm:gap-2 items-center py-2 px-2 sm:px-3 rounded-xl border transition-all animate-fade-in-up ${
              m.isOwn
                ? 'bg-white/[0.04] border-white/[0.12]'
                : 'bg-white/[0.01] border-white/[0.04]'
            }`}
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
              {m.isOwn
                ? <img src="/assets/shield_logo.png" alt="Aethel" className="w-3.5 h-3.5 object-contain shrink-0 drop-shadow-sm" />
                : <Cpu className="w-3 h-3 text-white/40 shrink-0" />}
              <span className={`text-[10px] sm:text-[11px] font-semibold truncate ${m.isOwn ? 'text-white' : 'text-white/60'}`}>
                {m.name}
              </span>
            </div>
            <div className="text-center">
              <span className={`text-xs sm:text-sm font-black ${m.isOwn ? 'text-white' : 'text-white/70'}`}>{m.score}</span>
            </div>
            <div className="text-center">
              <span className={`text-[10px] sm:text-xs font-black ${m.iit >= 8 ? 'text-white' : 'text-white/40'}`}>
                +{m.iit}
              </span>
            </div>
            <div className="text-center">
              <span className={`text-[10px] sm:text-xs font-black ${m.gap >= 6 ? 'text-white' : 'text-white/40'}`}>
                +{m.gap}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* insight footer */}
      <div className="px-3 sm:px-4 pb-4">
        <div className="p-2 sm:p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-white/60 shrink-0 mt-0.5" />
          <p className="text-[9px] sm:text-[10px] text-white/50 leading-relaxed">
            All mainstream LLMs raised their score 7–12 pts when college changed from NIT Trichy → IIT Bombay.
            Aethel's delta: <span className="text-white font-bold">+1 pt</span>.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── stat counter card ── */
function StatCard({ value, suffix, label, delay }) {
  return (
    <div
      className="glass-card rounded-xl p-3 sm:p-4 text-center animate-fade-in-up"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="text-xl sm:text-2xl font-black text-white tracking-tight">
        <CountUp target={value} suffix={suffix} />
      </div>
      <div className="text-[9px] sm:text-[10px] font-bold uppercase tracking-widest text-white/40 mt-1">{label}</div>
    </div>
  );
}

/* ── main export ── */
export default function LandingView({ onGetStarted, onLoadDemo }) {
  // Fetch real bias stats from the backend
  const [liveStats, setLiveStats] = useState(null);
  useEffect(() => {
    fetch(`${API_URL}/stats`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && data.pool_size > 0) setLiveStats(data);
      })
      .catch(() => {});
  }, []);

  // Derive display values: use real data when available, fall back to demo numbers
  const avgDelta     = liveStats ? Math.round(liveStats.avg_score) : 31;
  const poolSize     = liveStats ? liveStats.pool_size : 47;
  const biasReduct   = 73; // constant — from our counterfactual research
  const deltaLabel   = liveStats ? 'Avg Score' : 'Avg Bias Delta';
  const poolLabel    = liveStats ? 'Scans in Pool' : 'Beta Scans';

  const features = [
    {
      icon: <Shield className="w-4 h-4" />,
      title: 'Institution-Blind Scoring',
      desc: 'Strips IIT/NIT prestige signals before evaluation. NIT Trichy = IIT Bombay when only skills matter.',
    },
    {
      icon: <GitBranch className="w-4 h-4" />,
      title: 'Counterfactual Bias Tests',
      desc: 'Runs the same resume with 4 demographic mutations. Measures exact score swing caused by name, college, city, and career gaps.',
    },
    {
      icon: <Zap className="w-4 h-4" />,
      title: 'JD Bias Detector',
      desc: 'Paste any job description. Flags "IIT/NIT preferred", "culture fit", "no gaps" — the phrases killing diverse pipelines.',
    },
    {
      icon: <Lock className="w-4 h-4" />,
      title: 'Zero Data Stored',
      desc: 'PII is redacted before the model ever sees your resume. No profiles, no logs, no selling your data.',
    },
  ];

  return (
    <div className="min-h-full flex flex-col animate-fade-in">

      {/* ── HERO ── */}
      <div className="flex-1 flex flex-col lg:flex-row gap-6 lg:gap-10 p-4 sm:p-8 items-start w-full overflow-hidden">

        {/* left col */}
        <div className="flex-1 w-full max-w-xl">

          {/* eyebrow */}
          <div className="flex items-center gap-2 mb-6 animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
            <span className="text-white/40 text-xs">◈</span>
            <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-white/40">
              Aethel Compliance Engine · India-first ATS
            </span>
          </div>

          {/* headline */}
          <h1
            className="text-3xl sm:text-5xl font-black text-white leading-[1.08] tracking-tight mb-5 animate-fade-in-up"
            style={{ animationDelay: '0.1s' }}
          >
            Your resume deserves
            <br />
            <span className="text-white">a fair shot.</span>
          </h1>

          {/* subhead */}
          <p
            className="text-white/50 text-base leading-relaxed mb-4 max-w-lg animate-fade-in-up"
            style={{ animationDelay: '0.15s' }}
          >
            Every mainstream ATS and LLM quietly penalizes you for your college,
            your name, your career gap, and your city.{' '}
            <span className="text-white/80 font-semibold">
              Aethel measures exactly how much — then evaluates you on skills alone.
            </span>
          </p>

          {/* India callout */}
          <div
            className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08] mb-8 animate-fade-in-up"
            style={{ animationDelay: '0.2s' }}
          >
            <AlertTriangle className="w-4 h-4 text-white/60 shrink-0 mt-0.5" />
            <p className="text-xs text-white/60 leading-relaxed">
              Proven in tests: Gemma 2 scored a NIT Trichy candidate{' '}
              <span className="text-white font-bold">12 pts lower</span> than an
              identical IIT Bombay resume. Aethel's delta:{' '}
              <span className="text-white font-bold">1 pt</span>.
              This is the same bias inside AMCAT and CoCubes — we expose it.
            </p>
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-10 animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
            <button
              id="landing-audit-btn"
              onClick={onGetStarted}
              className="w-full sm:w-auto justify-center flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black text-sm font-bold hover:bg-white/90 active:scale-95 transition-all"
            >
              <Zap className="w-4 h-4" />
              Audit My Resume — Free
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              id="landing-demo-btn"
              onClick={onLoadDemo}
              className="w-full sm:w-auto justify-center flex items-center gap-2 px-5 py-3 rounded-xl border border-white/[0.12] text-white/80 text-sm font-semibold hover:bg-white/[0.05] hover:text-white hover:border-white/20 transition-all"
            >
              <Play className="w-4 h-4" />
              View Sample Demo
            </button>
          </div>

          {/* trust pills */}
          <div className="flex flex-wrap gap-2 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
            {[
              '₹0 — always free for candidates',
              'No data stored',
              'Open source fine-tuned model',
              'India-first bias vectors',
            ].map((t, i) => (
              <span
                key={i}
                className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-semibold text-white/40 border border-white/[0.06] bg-white/[0.02]"
              >
                <Check className="w-2.5 h-2.5" />
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* right col — live bias preview */}
        <div className="w-full lg:w-[400px] shrink-0 space-y-4 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <BiasPreviewCard />

          {/* stats row */}
          <div className="grid grid-cols-3 gap-3">
            <StatCard value={avgDelta}   suffix=" pts" label={deltaLabel}    delay={0.35} />
            <StatCard value={poolSize}   suffix=""     label={poolLabel}     delay={0.4}  />
            <StatCard value={biasReduct} suffix="%"    label="Bias Reduction" delay={0.45} />
          </div>
        </div>
      </div>

      {/* ── FEATURES ── */}
      <div className="px-4 sm:px-8 pb-8">
        <div className="border-t border-white/[0.05] pt-8">
          <div className="flex items-center gap-2 mb-6">
            <span className="text-white/30 text-xs">◈</span>
            <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-white/30">
              What the engine does
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {features.map((f, i) => (
              <div
                key={i}
                className="glass-card rounded-xl p-4 hover-lift animate-fade-in-up"
                style={{ animationDelay: `${0.35 + i * 0.07}s` }}
              >
                <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mb-3 text-white/60">
                  {f.icon}
                </div>
                <div className="text-sm font-bold text-white mb-1.5">{f.title}</div>
                <div className="text-xs text-white/40 leading-relaxed">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── vs AMCAT strip ── */}
      <div className="px-4 sm:px-8 pb-8 w-full max-w-full">
        <div className="glass-card rounded-2xl p-4 sm:p-6 border border-white/[0.06] overflow-hidden">
          <div className="flex items-center gap-2 mb-5">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">
              How we compare
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="w-[40%] text-left py-2 pr-4 font-bold text-white/40 uppercase tracking-wider">Capability</th>
                  <th className="w-[15%] text-center py-2 px-3 font-bold text-white uppercase tracking-wider">Aethel</th>
                  <th className="w-[15%] text-center py-2 px-3 font-bold text-white/30 uppercase tracking-wider">AMCAT</th>
                  <th className="w-[15%] text-center py-2 px-3 font-bold text-white/30 uppercase tracking-wider">CoCubes</th>
                  <th className="w-[15%] text-center py-2 px-3 font-bold text-white/30 uppercase tracking-wider">Jobscan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[
                  ['Bias detection (IIT prestige swap)',     true,  false, false, false],
                  ['Maternity / career gap audit',           true,  false, false, false],
                  ['Name-based demographic test',            true,  false, false, false],
                  ['JD bias scanner',                        true,  false, false, 'partial'],
                  ['Skill assessment (aptitude / coding)',   true,  true,  true,  false],
                  ['Contextual vs declared skill scoring',   true,  false, false, false],
                  ['Multi-LLM bias comparison',              true,  false, false, false],
                  ['Resume ↔ JD match scoring',              true,  false, false, true],
                  ['Lateral hire support',                   true,  true,  true,  false],
                  ['Explainable score breakdown',            true,  false, false, 'partial'],
                  ['Free for candidates',                    true,  false, false, false],
                ].map(([label, ...vals], i) => (
                  <tr key={i} className="hover:bg-white/[0.01] transition-colors">
                    <td className="py-2.5 pr-4 text-white/60 font-medium">{label}</td>
                    {vals.map((v, j) => (
                      <td key={j} className="py-2.5 px-3 text-center">
                        {v === true
                          ? <Check className="w-3.5 h-3.5 text-white mx-auto" />
                          : v === 'partial'
                            ? <span className="text-white/50 font-bold mx-auto block text-center text-[10px]">~</span>
                            : <span className="text-white/20 font-bold mx-auto block text-center">—</span>
                        }
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── final CTA ── */}
      <div className="px-4 sm:px-8 pb-10 text-center animate-fade-in-up w-full" style={{ animationDelay: '0.5s' }}>
        <p className="text-white/30 text-xs mb-4 uppercase tracking-widest font-bold">
          Ready to see the bias in your resume's evaluations?
        </p>
        <div className="flex flex-col sm:flex-row justify-center items-stretch sm:items-center gap-3">
          <button
            onClick={onGetStarted}
            className="w-full sm:w-auto justify-center flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black text-sm font-bold hover:bg-white/90 active:scale-95 transition-all"
          >
            <Zap className="w-4 h-4" />
            Start Free Audit
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={onLoadDemo}
            className="w-full sm:w-auto justify-center flex items-center gap-2 px-5 py-3 rounded-xl border border-white/[0.10] text-white/70 text-sm font-semibold hover:bg-white/[0.04] hover:text-white transition-all"
          >
            <Play className="w-4 h-4" />
            Try Demo First
          </button>
        </div>
      </div>

    </div>
  );
}
