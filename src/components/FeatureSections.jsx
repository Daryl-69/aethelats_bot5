import React, { useState, useEffect } from 'react';
import { Fingerprint, ChevronUp, ChevronDown, ChevronRight, Percent, Brain, TrendingUp, TrendingDown, BookOpen } from 'lucide-react';
import { SectionHeading, AnimatedBar, useCountUp } from './UIHelpers';

export function PercentileBadge({ percentile, poolSize }) {
  const top = 100 - percentile;
  return (
    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 bg-white/[0.04]">
      <Percent className="w-4 h-4 text-white" />
      <div>
        <div className="text-sm font-black text-white leading-none">Top {top}%</div>
        <div className="text-xs text-white/80 mt-0.5">of {poolSize} candidates</div>
      </div>
    </div>
  );
}

export function PIIStripPanel({ items }) {
  const [open, setOpen] = useState(false);
  if (!items || items.length === 0) return null;
  return (
    <div className="mb-6 rounded-2xl border border-white/[0.08] glass-card glass-card-hover overflow-hidden">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-white/[0.03] transition-colors">
        <Fingerprint className="w-5 h-5 text-white/90 shrink-0" />
        <div className="flex-1">
          <div className="text-sm font-semibold text-white">PII Stripped — {items.length} item{items.length !== 1 ? 's' : ''} removed</div>
          <div className="text-xs text-white/80 mt-0.5">Resume evaluated in blind mode.</div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/80" /> : <ChevronDown className="w-4 h-4 text-white/80" />}
      </button>
      {open && (
        <div className="px-5 pb-4 border-t border-white/[0.06]">
          <div className="mt-3 flex flex-wrap gap-2">
            {items.map((item, i) => (
              <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-xs">
                <span className="line-through text-white/90 font-mono">{item}</span>
                <ChevronRight className="w-3 h-3 text-white" />
                <span className="text-white font-mono">[REDACTED]</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SkillDepthSection({ breakdown, contextualRatio, stuffingDetected }) {
  if (!breakdown || breakdown.length === 0) return null;
  const contextual = breakdown.filter(s => s.usage_type === 'contextual');
  const declarative = breakdown.filter(s => s.usage_type === 'declarative');
  const pct = Math.round((contextualRatio || 0) * 100);
  return (
    <section className="mb-6 animate-fade-in-up stagger-4">
      <SectionHeading icon={<Brain className="w-3.5 h-3.5" />} label="Skill Depth Analysis" />
      <div className="glass-card glass-card-hover rounded-2xl p-6 scroll-animate">
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-white/90">Contextual Skills</span>
            <span className="text-sm font-black text-white">{pct}%</span>
          </div>
          <AnimatedBar value={pct} color="bg-white" />
          <div className="flex justify-between text-xs text-white mt-1.5">
            <span>Contextual ({contextual.length})</span>
            <span>Declarative ({declarative.length})</span>
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div>
            <div className="text-xs font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" /> Demonstrated
            </div>
            <div className="space-y-2">
              {contextual.map((s, i) => (
                <div key={i} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 hover-lift">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-semibold text-white/80">{s.skill}</span>
                    <span className="text-xs font-black text-white">{s.impact_score}</span>
                  </div>
                  <AnimatedBar value={s.impact_score} delay={i * 100} color="bg-white/60" />
                  <p className="text-xs text-white italic mt-1.5">"{s.evidence}"</p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-bold text-white/80 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <TrendingDown className="w-3.5 h-3.5" /> Mentioned Only
            </div>
            <div className="space-y-2">
              {declarative.map((s, i) => (
                <div key={i} className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 hover-lift">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-semibold text-white">{s.skill}</span>
                    <span className="text-xs font-black text-white/90">{s.impact_score}</span>
                  </div>
                  <AnimatedBar value={s.impact_score} delay={i * 100} color="bg-white/30" />
                  <p className="text-xs text-white italic mt-1.5">"{s.evidence}"</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SkillMatchSection({ matches }) {
  if (!matches || matches.length === 0) return null;
  const exact = matches.filter(m => m.match_type === 'exact');
  const synonyms = matches.filter(m => m.match_type === 'synonym');
  const adjacent = matches.filter(m => m.match_type === 'adjacency');
  return (
    <section className="mb-6 animate-fade-in-up stagger-5">
      <SectionHeading icon={<BookOpen className="w-3.5 h-3.5" />} label="Skill Knowledge Graph — Matches" />
      <div className="glass-card glass-card-hover rounded-2xl p-5 scroll-animate">
        <div className="flex items-center gap-4 mb-4 text-xs flex-wrap">
          <span className="flex items-center gap-1.5 text-white"><span className="w-2.5 h-2.5 rounded-full bg-white/60" />{exact.length} Exact</span>
          <span className="flex items-center gap-1.5 text-white/90"><span className="w-2.5 h-2.5 rounded-full bg-white/40" />{synonyms.length} Synonym</span>
          <span className="flex items-center gap-1.5 text-white/80"><span className="w-2.5 h-2.5 rounded-full bg-white/25" />{adjacent.length} Adjacency</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {matches.map((m, i) => {
            const c = m.match_type === 'exact' ? 'bg-white/[0.08] border-white/15 text-white' : m.match_type === 'synonym' ? 'bg-white/[0.05] border-white/10 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/90';
            return (
              <div key={i} className={'flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium hover-lift ' + c}>
                <span className="font-mono font-bold">{m.found_in_resume}</span>
                {m.match_type !== 'exact' && (<><ChevronRight className="w-3 h-3 opacity-50" /><span className="opacity-70">{m.canonical_name}</span></>)}
                <span className="text-[10px] px-1.5 py-0.5 rounded-md font-bold uppercase ml-1 bg-white/[0.06]">{m.match_type}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
