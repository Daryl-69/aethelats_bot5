import React, { useState } from 'react';
import { FileText, ChevronUp, ChevronDown, RefreshCw, AlertTriangle, Globe, Zap, FlaskConical, Shield, Check, Github, Linkedin, Code, Database, Link } from 'lucide-react';
import { SEVERITY_STYLE } from './constants';
import { SectionHeading } from './UIHelpers';

const PlatformIcon = ({ platform, className }) => {
  const p = platform?.toLowerCase() || '';
  if (p === 'github') return <Github className={className} />;
  if (p === 'linkedin') return <Linkedin className={className} />;
  if (p === 'leetcode' || p === 'hackerrank' || p === 'codeforces') return <Code className={className} />;
  if (p === 'kaggle') return <Database className={className} />;
  if (p === 'portfolio' || p === 'medium' || p === 'devto') return <Globe className={className} />;
  return <Link className={className} />;
};

export function JDResultPanel({ result }) {
  const score = result.overall_bias_score || 70;
  const JD_TYPE_LABELS = { masculine_coded:'Masculine-Coded', age_discriminatory:'Age Disc.', origin_coded:'Origin', ableist:'Ableist', socioeconomic:'Socioeconomic', culture_fit:'Culture Fit', gendered_title:'Gendered' };
  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center gap-4 p-4 rounded-xl glass-card">
        <div className="text-center shrink-0"><div className="text-4xl font-black text-white">{score}</div><div className="text-xs text-white/80 mt-0.5">Inclusivity</div></div>
        <div className="flex-1">
          <span className="inline-flex items-center px-3 py-1 rounded-lg border border-white/10 text-sm font-bold mb-1 bg-white/[0.05] text-white">{result.bias_level}</span>
          <p className="text-xs text-white/90 leading-relaxed">{result.summary}</p>
        </div>
      </div>
      {result.flagged_phrases?.length > 0 && (
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-white/80 mb-2">{result.flagged_phrases.length} Biased Phrases</div>
          <div className="space-y-2">{result.flagged_phrases.map((p, i) => (
            <div key={i} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
              <div className="flex flex-wrap gap-2 mb-1.5">
                <code className="text-xs px-2 py-0.5 rounded bg-white/[0.06] text-white font-mono">"{p.phrase}"</code>
                <span className="text-xs px-2 py-0.5 rounded bg-white/[0.04] text-white/90 border border-white/[0.06]">{JD_TYPE_LABELS[p.bias_type] || p.bias_type}</span>
              </div>
              <p className="text-xs text-white/80 leading-relaxed">{p.explanation}</p>
              {p.neutral_alternative && <p className="text-xs text-white mt-1.5">✓ Try: <em>"{p.neutral_alternative}"</em></p>}
            </div>
          ))}</div>
        </div>
      )}
      {result.rewrite_suggestions?.length > 0 && (
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="text-xs font-bold text-white mb-2">Rewrite Suggestions</div>
          <ul className="space-y-1">{result.rewrite_suggestions.map((s, i) => <li key={i} className="text-xs text-white/90">• {s}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

export function JDAnalysisSection({ jdText, setJdText, jdResult, analyzing, onAnalyze, expanded, setExpanded, isDemo, demoResult }) {
  function handleAnalyze() { if (isDemo) { onAnalyze(demoResult); return; } onAnalyze(); }
  return (
    <div className="mt-6 rounded-2xl border border-white/[0.08] glass-card glass-card-hover overflow-hidden">
      <button onClick={() => setExpanded(e => !e)} className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-white/[0.03] transition-colors">
        <FileText className="w-5 h-5 text-white/90 shrink-0" />
        <div className="flex-1">
          <div className="text-sm font-semibold text-white">Analyze Job Description for Bias</div>
          <div className="text-xs text-white/80 mt-0.5">Research-backed detection of exclusionary language</div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-white/80" /> : <ChevronDown className="w-4 h-4 text-white/80" />}
      </button>
      {expanded && (
        <div className="px-5 pb-5 border-t border-white/[0.06]">
          {!isDemo && <textarea value={jdText} onChange={e => setJdText(e.target.value)} placeholder="Paste job description here..." className="w-full h-36 mt-4 glass-input rounded-xl px-4 py-3 text-sm text-white placeholder-white/20 resize-none" />}
          <button onClick={handleAnalyze} disabled={analyzing || (!isDemo && !jdText.trim())} className={'mt-3 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 ' + (analyzing || (!isDemo && !jdText.trim()) ? 'opacity-40 cursor-not-allowed bg-white/[0.05] text-white/80' : 'bg-white/[0.08] border border-white/10 text-white hover:bg-white/[0.12] active:scale-95')}>
            {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <AlertTriangle className="w-4 h-4" />}
            {analyzing ? 'Analyzing...' : isDemo ? 'View Demo Results' : 'Detect Bias'}
          </button>
          {jdResult && <JDResultPanel result={jdResult} />}
        </div>
      )}
    </div>
  );
}

export function ProofOfWorkSection({ detectedLinks, proofResult, isLoading, onFetch, isDemo }) {
  if (!detectedLinks?.length && !proofResult) return null;
  if (!proofResult && !isLoading) {
    return (
      <section className="mb-6 animate-fade-in-up stagger-6">
        <SectionHeading icon={<Globe className="w-3.5 h-3.5" />} label={'Proof of Work — ' + detectedLinks.length + ' Links'} />
        <div className="glass-card glass-card-hover rounded-2xl p-6">
          <div className="flex flex-wrap gap-2 mb-4">{detectedLinks.map((l, i) => (
            <span key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-white">
              <PlatformIcon platform={l.platform} className="w-3.5 h-3.5 text-white/70" />
              <span className="capitalize font-medium">{l.platform}</span>
            </span>
          ))}</div>
          <div className="flex items-start gap-4">
            <div className="flex-1 text-xs text-white/80 leading-relaxed">Fetch live data from GitHub, LeetCode and more.</div>
            <button onClick={onFetch} className="px-5 py-2.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/10 text-white text-sm font-semibold transition-all flex items-center gap-2 shrink-0 active:scale-95 hover-lift">
              <Globe className="w-4 h-4" />{isDemo ? 'View Demo' : 'Fetch'}
            </button>
          </div>
        </div>
      </section>
    );
  }
  if (isLoading) {
    return (
      <section className="mb-6"><SectionHeading icon={<Globe className="w-3.5 h-3.5" />} label="Proof of Work — Fetching..." />
        <div className="glass-card glass-card-hover rounded-2xl p-8 flex flex-col items-center gap-4">
          <div className="relative w-16 h-16"><div className="absolute inset-0 rounded-full bg-white/10 animate-ping" style={{animationDuration:'2s'}} />
            <div className="relative w-full h-full bg-black border-2 border-white/20 rounded-full flex items-center justify-center"><Globe className="w-7 h-7 text-white/90 animate-pulse" /></div>
          </div>
          <p className="text-sm text-white/90 text-center">Fetching live platform data...</p>
        </div>
      </section>
    );
  }
  const proof = proofResult;
  const score = proof.overall_proof_score || 0;
  return (
    <section className="mb-6 animate-fade-in-up stagger-6">
      <SectionHeading icon={<Globe className="w-3.5 h-3.5" />} label="Proof of Work — Results" />
      <div className="glass-card glass-card-hover rounded-2xl p-6">
        <div className="flex items-center gap-6 mb-5 pb-5 border-b border-white/[0.06]">
          <div className="text-center shrink-0"><div className="text-5xl font-black text-white">{score}</div><div className="text-xs text-white/80 mt-1">Evidence Score</div></div>
          <div className="flex-1">
            <div className="inline-flex items-center px-3 py-1.5 rounded-lg border border-white/10 text-sm font-bold mb-2 bg-white/[0.05] text-white">{proof.proof_level}</div>
            <p className="text-xs text-white/90 leading-relaxed">{proof.summary}</p>
          </div>
        </div>
        {proof.key_signals?.length > 0 && (
          <div className="mb-4"><div className="text-xs text-white/80 font-semibold uppercase tracking-wider mb-2">Key Signals</div>
            <div className="flex flex-wrap gap-2">{proof.key_signals.map((s, i) => <span key={i} className="px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-white">✓ {s}</span>)}</div>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          {(proof.platform_data || []).filter(p => p.signals?.length > 0).map((p, i) => (
            <div key={i} className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-3 hover-lift">
              <div className="flex items-center gap-2 mb-2">
                <PlatformIcon platform={p.platform} className="w-4 h-4 text-white/80" />
                <span className="text-sm font-semibold text-white capitalize">{p.platform}</span>
                {p.username && <span className="text-xs text-white/80">@{p.username}</span>}
                <span className={'ml-auto text-xs px-2 py-0.5 rounded font-bold ' + (p.status === 'fetched' ? 'bg-white/[0.06] text-white' : 'bg-white/[0.03] text-white/80')}>{p.status === 'fetched' ? '● Live' : '○ Detected'}</span>
              </div>
              <div className="space-y-0.5">{p.signals.map((s, j) => <div key={j} className="text-xs text-white/80">• {s}</div>)}</div>
            </div>
          ))}
        </div>
        {proof.ats_override_recommendation && proof.ats_override_recommendation !== 'None' && (
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-white leading-relaxed">
            <Zap className="w-3.5 h-3.5 inline mr-1.5" /><strong>Override ({proof.ats_override_recommendation}):</strong> {proof.bias_blind_verdict}
          </div>
        )}
      </div>
    </section>
  );
}

export function BiasStabilitySection({ cfResult, isRunning, onRunTest, isDemo }) {
  if (!cfResult && !isRunning) {
    return (
      <section className="mb-6 animate-fade-in-up stagger-7">
        <SectionHeading icon={<FlaskConical className="w-3.5 h-3.5" />} label="Bias Stability Test" />
        <div className="glass-card glass-card-hover rounded-2xl p-6 flex items-center gap-5">
          <div className="w-12 h-12 rounded-xl bg-white/[0.05] border border-white/10 flex items-center justify-center shrink-0"><FlaskConical className="w-6 h-6 text-white/90" /></div>
          <div className="flex-1"><h4 className="text-sm font-semibold text-white mb-1">Test AI Bias Stability</h4><p className="text-xs text-white/80 leading-relaxed">Simulates 3 demographic swap experiments.</p></div>
          <button onClick={onRunTest} className="px-5 py-2.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/10 text-white text-sm font-semibold transition-all flex items-center gap-2 shrink-0 hover-lift">
            <FlaskConical className="w-4 h-4" />{isDemo ? 'View Demo' : 'Run Test'}
          </button>
        </div>
      </section>
    );
  }
  if (isRunning) {
    return (
      <section className="mb-6"><SectionHeading icon={<FlaskConical className="w-3.5 h-3.5" />} label="Bias Stability — Running..." />
        <div className="glass-card glass-card-hover rounded-2xl p-8 flex flex-col items-center gap-4 scan-container">
          <div className="relative w-16 h-16"><div className="absolute inset-0 rounded-full bg-white/10 animate-ping" style={{animationDuration:'2s'}} />
            <div className="relative w-full h-full bg-black border-2 border-white/20 rounded-full flex items-center justify-center"><FlaskConical className="w-7 h-7 text-white/90 animate-pulse" /></div>
          </div>
          <p className="text-sm text-white/90 text-center">Running demographic swap experiments...</p>
        </div>
      </section>
    );
  }
  const stab = cfResult.bias_stability_score || 75;
  const interp = cfResult.interpretation || 'moderate_bias';
  const interpLabel = { stable: '✓ Stable', moderate_bias: '⚠ Moderate Sensitivity', high_bias: '✗ High Sensitivity' };
  return (
    <section className="mb-6 animate-fade-in-up stagger-7">
      <SectionHeading icon={<FlaskConical className="w-3.5 h-3.5" />} label="Bias Stability — Results" />
      <div className="glass-card glass-card-hover rounded-2xl p-6">
        <div className="flex items-center gap-6 mb-5 pb-5 border-b border-white/[0.06]">
          <div className="text-center shrink-0"><div className="text-5xl font-black text-white">{stab}</div><div className="text-xs text-white/80 mt-1">Stability</div></div>
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 text-sm font-bold mb-2 bg-white/[0.05] text-white">{interpLabel[interp] || interp}</div>
            <p className="text-xs text-white/90 leading-relaxed">{cfResult.summary}</p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-xs text-white/80 font-semibold uppercase tracking-wider mb-2">{cfResult.measured ? 'Measured Changes:' : 'Simulated Changes:'}</div>
          <div className="grid grid-cols-12 gap-2 text-xs font-bold uppercase tracking-wider text-white px-3 pb-1 border-b border-white/[0.06]">
            <div className="col-span-5">Scenario</div><div className="col-span-2 text-center">Score</div><div className="col-span-2 text-center">Δ</div><div className="col-span-3">Reasoning</div>
          </div>
          <div className="grid grid-cols-12 gap-2 items-start px-3 py-2.5 bg-white/[0.02] rounded-xl">
            <div className="col-span-5 text-xs font-semibold text-white">Baseline</div>
            <div className="col-span-2 text-center text-sm font-black text-white">{cfResult.baseline_score}</div>
            <div className="col-span-2 text-center text-xs text-white/80">—</div>
            <div className="col-span-3 text-xs text-white/80 italic">Blind score</div>
          </div>
          {(cfResult.variants || []).map((v, i) => {
            const isRed = v.delta > 3;
            return (
              <div key={i} className={'grid grid-cols-12 gap-2 items-start px-3 py-2.5 rounded-xl border animate-table-row ' + (isRed ? 'bg-white/[0.03] border-white/10' : 'bg-white/[0.01] border-white/[0.04]')} style={{ animationDelay: (i * 0.1) + 's' }}>
                <div className="col-span-5 text-xs font-semibold text-white">{v.label}</div>
                <div className="col-span-2 text-center text-sm font-black text-white/80">{v.simulated_score}</div>
                <div className={'col-span-2 text-center text-sm font-black ' + (isRed ? 'text-white' : 'text-white')}>{v.delta >= 0 ? '+' : ''}{v.delta}</div>
                <div className="col-span-3 text-xs text-white/80 leading-relaxed">{v.reasoning}</div>
              </div>
            );
          })}
        </div>
        {cfResult.intersectional && (
          <div className="mt-4 p-4 rounded-xl border border-white/[0.08] bg-white/[0.02] text-xs leading-relaxed">
            <div className="font-bold text-sm text-white mb-2">Intersectional Analysis</div>
            <div className="flex items-center gap-6 mb-2 text-white">
              <div>Combined Δ: <span className="font-black text-white">+{cfResult.intersectional.combined_delta}</span></div>
              <div>Sum Δ: <span className="font-black text-white">+{cfResult.intersectional.sum_of_individual_deltas}</span></div>
              <div>Factor: <span className="font-black text-white">{cfResult.intersectional.amplification_factor}x</span></div>
            </div>
            <p className="text-white/90">{cfResult.intersectional.explanation}</p>
          </div>
        )}
      </div>
    </section>
  );
}
