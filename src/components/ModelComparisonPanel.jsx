import React, { useState } from 'react';
import { Cpu, ChevronDown, ChevronUp, AlertTriangle, Shield, Zap, BarChart3, Info, TrendingUp, TrendingDown } from 'lucide-react';
import { SectionHeading } from './UIHelpers';
import SkillKnowledgeGraph from './SkillKnowledgeGraph';

/* ─── Colour helpers ─────────────────────────────────────────── */
const deltaColor  = (d) => Math.abs(d) > 8 ? 'text-red-400' : Math.abs(d) > 3 ? 'text-yellow-400' : 'text-white';
const deltaSign   = (d) => (d >= 0 ? '+' : '') + d;
const scoreColor  = (s) => s >= 75 ? 'text-emerald-400' : s >= 55 ? 'text-yellow-300' : 'text-red-400';
const barColor    = (s) => s >= 75 ? 'bg-emerald-400/60' : s >= 55 ? 'bg-yellow-400/60' : 'bg-red-400/60';

/* ─── Tiny score bar ─────────────────────────────────────────── */
function MiniBar({ value, max = 100, color = 'bg-white/30' }) {
  return (
    <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden relative">
      <div className={`h-full rounded-full ${color} animate-bar-fill`} style={{ width: `${(value / max) * 100}%` }} />
    </div>
  );
}

/* ─── Radar diff cell ────────────────────────────────────────── */
function RadarDiff({ fairai, other, label }) {
  const diff = fairai - other;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 shrink-0 text-white/90 truncate">{label}</span>
      <div className="flex-1">
        <MiniBar value={fairai} color="bg-white/40" />
      </div>
      <span className="w-8 text-right font-bold text-white">{fairai}</span>
      <span className={`w-12 text-right font-bold ${diff >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
        {deltaSign(diff)}
      </span>
    </div>
  );
}

/* ─── Strengths & Gaps side-by-side ─────────────────────────── */
function SignalsGapsPanel({ signals = [], gaps = [], isOwn }) {
  const accent = isOwn ? 'bg-emerald-400/[0.04] border-emerald-400/10' : 'bg-white/[0.02] border-white/[0.06]';
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
      {/* Strong signals */}
      <div className={`rounded-xl border p-3 ${accent}`}>
        <div className="flex items-center gap-1.5 mb-2">
          <TrendingUp className="w-3.5 h-3.5 text-white/80" />
          <span className="text-xs font-bold text-white/90 uppercase tracking-wider">
            Strong Signals ({signals.length})
          </span>
        </div>
        {signals.length === 0 ? (
          <p className="text-xs text-white italic">None detected</p>
        ) : (
          <div className="space-y-2">
            {signals.map((sig, i) => (
              <div key={i} className={`flex items-start gap-2 animate-slide-in-right stagger-${(i % 8) + 1}`}>
                <div className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0 ${isOwn ? 'bg-emerald-400/60 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-white/30'}`} />
                <div>
                  <div className="text-xs font-semibold text-white">{sig.signal}</div>
                  {sig.evidence && sig.evidence !== sig.signal && (
                    <div className="text-[10px] text-white italic mt-0.5">"{sig.evidence}"</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Gaps */}
      <div className={`rounded-xl border p-3 ${accent}`}>
        <div className="flex items-center gap-1.5 mb-2">
          <TrendingDown className="w-3.5 h-3.5 text-white" />
          <span className="text-xs font-bold text-white/80 uppercase tracking-wider">
            Gaps ({gaps.length})
          </span>
        </div>
        {gaps.length === 0 ? (
          <p className="text-xs text-white italic">No gaps flagged</p>
        ) : (
          <div className="space-y-2">
            {gaps.map((g, i) => (
              <div key={i} className={`flex items-start gap-2 animate-slide-in-right stagger-${(i % 8) + 2}`}>
                <div className="w-1.5 h-1.5 rounded-full mt-1 shrink-0 bg-white/15" />
                <div>
                  <div className="text-xs font-semibold text-white">{g.gap}</div>
                  <div className="text-[10px] text-white mt-0.5">
                    {g.severity === 'blocking' ? '⚠ Blocking' : 'Minor'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Skills pill list ───────────────────────────────────────── */
function SkillsPills({ matches = [], isOwn }) {
  if (!matches || matches.length === 0) return null;
  return (
    <div className="mt-3">
      <div className="text-[10px] font-bold uppercase tracking-wider text-white mb-1.5">
        Skills Detected ({matches.length})
      </div>
      <div className="flex flex-wrap gap-1.5">
        {matches.map((m, i) => (
          <span
            key={i}
            className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold animate-scale-in stagger-${(i % 8) + 1} ${
              isOwn
                ? 'bg-emerald-400/10 border-emerald-400/20 text-emerald-300 hover-glow hover-lift'
                : 'bg-white/[0.04] border-white/[0.08] text-white/90 hover-glow hover-lift'
            }`}
          >
            {m.canonical_name || m.found_in_resume}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ─── Single model card ──────────────────────────────────────── */
function ModelCard({ model, fairaiScore, isOwnModel }) {
  const [expandedTab, setExpandedTab] = useState(null); // null | 'radar' | 'signals' | 'graph'
  const advantage = fairaiScore - model.score;

  const hasSignals = (model.strong_signals?.length > 0) || (model.gaps?.length > 0);
  const hasGraph   = model.skill_matches?.length > 0;

  const toggleTab = (tab) => setExpandedTab(prev => prev === tab ? null : tab);

  const tabs = [
    { id: 'radar',   label: 'Radar',   show: !!model.radar && Object.keys(model.radar).length > 0 },
    { id: 'signals', label: 'Signals & Gaps', show: hasSignals },
    { id: 'graph',   label: 'Skill Graph',    show: hasGraph },
  ].filter(t => t.show);

  return (
    <div className={`rounded-2xl border transition-all duration-300 overflow-hidden hover-lift ${isOwnModel
      ? 'border-emerald-400/30 bg-emerald-400/[0.04] shadow-[0_0_24px_rgba(52,211,153,0.07)] hover:border-emerald-400/50'
      : 'border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15]'}`}>

      {/* Header */}
      <div className="px-5 py-4 flex items-center gap-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${isOwnModel ? 'bg-emerald-400/10 border-emerald-400/20' : 'bg-white/[0.04] border-white/10'}`}>
          {isOwnModel ? <Shield className="w-5 h-5 text-emerald-400" /> : <Cpu className="w-5 h-5 text-white/90" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <div className={`text-sm font-bold truncate ${isOwnModel ? 'text-emerald-300' : 'text-white'}`}>{model.label}</div>
            {isOwnModel && <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-400/15 text-emerald-400 border border-emerald-400/20 shrink-0">YOUR MODEL</span>}
          </div>
          <div className="text-xs text-white/80 mt-0.5 truncate">{model.provider} · {model.model_id}</div>
        </div>
        <div className="text-right shrink-0">
          <div className={`text-2xl font-black ${scoreColor(model.score)}`}>{model.score}</div>
          <div className="text-[10px] text-white/80">/ 100</div>
        </div>
        {!isOwnModel && (
          <div className="text-right shrink-0 ml-2">
            <div className={`text-sm font-black ${advantage >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {deltaSign(advantage)}
            </div>
            <div className="text-[10px] text-white/80">vs Aethel</div>
          </div>
        )}
      </div>

      {/* Quick row: verdict + bias delta chips */}
      <div className="px-5 pb-4 flex flex-wrap gap-2">
        <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white/[0.04] border border-white/[0.08] text-white">
          {model.recommendation}
        </span>
        {model.bias_deltas?.map((bd, i) => (
          <span key={i} className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${Math.abs(bd.delta) > 5
            ? 'bg-red-400/10 border-red-400/20 text-red-400'
            : 'bg-white/[0.04] border-white/[0.08] text-white/90'}`}>
            {bd.label}: {deltaSign(bd.delta)}
          </span>
        ))}
      </div>

      {/* Expandable section tabs */}
      {tabs.length > 0 && (
        <div className="px-5 pb-5 border-t border-white/[0.06] pt-3">
          <div className="flex gap-1 mb-3">
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => toggleTab(t.id)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all ${
                  expandedTab === t.id
                    ? (isOwnModel ? 'bg-emerald-400/15 text-emerald-300 border border-emerald-400/20' : 'bg-white/[0.08] text-white/80 border border-white/[0.12]')
                    : 'text-white/80 hover:text-white border border-transparent'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Radar tab */}
          {expandedTab === 'radar' && model.radar && (
            <div className="space-y-2.5 animate-fade-in-up">
              <div className="text-xs font-bold uppercase tracking-widest text-white mb-3">Radar Breakdown</div>
              {Object.entries(model.radar).map(([k, v], i) => (
                <div key={k} className={`animate-slide-in-right stagger-${(i % 8) + 1}`}>
                  <RadarDiff label={k.replace(/_/g, ' ')} fairai={fairaiScore} other={v} />
                </div>
              ))}
              {model.reasoning && (
                <p className="text-xs text-white/80 mt-3 pt-3 border-t border-white/[0.06] leading-relaxed italic animate-fade-in-up stagger-5">
                  "{model.reasoning}"
                </p>
              )}
            </div>
          )}

          {/* Signals & Gaps tab */}
          {expandedTab === 'signals' && (
            <div className="animate-scale-in">
              <SignalsGapsPanel signals={model.strong_signals || []} gaps={model.gaps || []} isOwn={isOwnModel} />
              <SkillsPills matches={model.skill_matches || []} isOwn={isOwnModel} />
            </div>
          )}

          {/* Skill Knowledge Graph tab */}
          {expandedTab === 'graph' && model.skill_matches?.length > 0 && (
            <div className="mt-2 rounded-xl overflow-hidden border border-white/[0.06] animate-fade-in" style={{ height: 340 }}>
              <SkillKnowledgeGraph skillData={model.skill_matches} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Bias verdict table ─────────────────────────────────────── */
function BiasVerdictTable({ models }) {
  const mutations = ['institution_delta', 'gap_delta', 'name_delta'];
  const mutLabels = { institution_delta: 'Institution → MIT', gap_delta: 'Gap Removed', name_delta: 'Name → Alex Johnson' };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-white/[0.06] text-white">
            <th className="text-left px-4 py-3 font-bold uppercase tracking-wider">Model</th>
            <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Score</th>
            {mutations.map(m => (
              <th key={m} className="text-center px-3 py-3 font-bold uppercase tracking-wider">{mutLabels[m]}</th>
            ))}
            <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Max Δ</th>
            <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Verdict</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {models.map((m, i) => {
            const isOwn = m.is_own_model;
            return (
              <tr key={i} className={`hover:bg-white/[0.02] transition-colors animate-table-row stagger-${(i % 8) + 1} ${isOwn ? 'bg-emerald-400/[0.03]' : ''}`}>
                <td className="px-4 py-3">
                  <div className={`font-bold ${isOwn ? 'text-emerald-300' : 'text-white'}`}>{m.label}</div>
                  {isOwn && <div className="text-[10px] text-emerald-400/70 mt-0.5">Fine-tuned · Bias-blind</div>}
                </td>
                <td className="text-center px-3 py-3">
                  <span className={`text-base font-black ${scoreColor(m.score)}`}>{m.score}</span>
                </td>
                {mutations.map(mk => {
                  const d = m.bias_deltas?.find(bd => bd.key === mk)?.delta ?? 0;
                  return (
                    <td key={mk} className="text-center px-3 py-3">
                      <span className={`font-black text-sm ${deltaColor(d)}`}>{deltaSign(d)}</span>
                      <div className="w-full mt-1">
                        <MiniBar value={Math.abs(d)} max={15} color={Math.abs(d) > 5 ? 'bg-red-400/50' : 'bg-white/20'} />
                      </div>
                    </td>
                  );
                })}
                <td className="text-center px-3 py-3">
                  <span className={`font-black px-2 py-0.5 rounded text-sm ${m.max_delta > 8 ? 'bg-red-400/10 text-red-400' : m.max_delta > 4 ? 'bg-yellow-400/10 text-yellow-400' : 'text-white/90'}`}>
                    {m.max_delta}
                  </span>
                </td>
                <td className="text-center px-3 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded font-bold border ${
                    isOwn ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' : 'bg-white/[0.04] text-white/90 border-white/[0.08]'
                  }`}>{m.recommendation}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Aggregate metrics banner ───────────────────────────────── */
function AggregateBanner({ data }) {
  const items = [
    { label: 'Aethel Advantage', value: `+${data.fairai_advantage_avg}`, sub: 'avg vs others', positive: true },
    { label: 'Cross-Model σ',   value: data.cross_model_variance,        sub: 'score std dev' },
    { label: 'Systemic Bias',   value: data.systemic_bias_detected ? 'YES' : 'NO', sub: 'all models agree', highlight: data.systemic_bias_detected },
    { label: 'Bias Reduction',  value: `${data.fairai_bias_reduction}%`, sub: 'Aethel vs avg Δ', positive: true },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      {items.map((it, i) => (
        <div key={i} className={`rounded-xl border p-4 text-center animate-counter-pop stagger-${(i % 8) + 1} ${it.positive ? 'border-emerald-400/20 bg-emerald-400/[0.04]' : it.highlight ? 'border-red-400/20 bg-red-400/[0.04]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
          <div className={`text-xl font-black ${it.positive ? 'text-emerald-400' : it.highlight ? 'text-red-400' : 'text-white/80'}`}>{it.value}</div>
          <div className="text-xs font-bold text-white mt-0.5">{it.label}</div>
          <div className="text-[10px] text-white mt-0.5">{it.sub}</div>
        </div>
      ))}
    </div>
  );
}

/* ─── Main export ────────────────────────────────────────────── */
export function ModelComparisonPanel({ compResult, isRunning, onRunTest, isDemo }) {
  const [activeTab, setActiveTab] = useState('cards');   // 'cards' | 'table'
  const data = compResult;
  const fairaiModel = data?.models?.find(m => m.is_own_model);
  const otherModels = data?.models?.filter(m => !m.is_own_model) ?? [];

  return (
    <section className="mb-6 animate-fade-in-up stagger-8">
      <SectionHeading icon={<BarChart3 className="w-3.5 h-3.5" />} label="LLM Comparison — Aethel vs Mainstream Models" />

      {!data ? (
        <div className="glass-card rounded-2xl p-8 text-center">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
            <BarChart3 className="w-7 h-7 text-white/80" />
          </div>
          <h4 className="text-base font-bold text-white mb-2">Compare Your Model vs Other LLMs</h4>
          <p className="text-sm text-white/80 mb-2 max-w-md mx-auto leading-relaxed">
            Runs the same resume through your fine-tuned Aethel model <em>and</em> mainstream LLMs (Llama 3.3, Gemma 4, Kimi K2 120B).
            Shows per-model skill graphs, signals, gaps, and bias sensitivity — side by side.
          </p>
          <p className="text-xs text-white mb-6 max-w-sm mx-auto">
            <Info className="w-3 h-3 inline mr-1" />
            This proves whether your unbiased model genuinely outperforms generic LLMs on fairness.
          </p>
          <button
            id="run-model-comparison-btn"
            onClick={onRunTest}
            disabled={isRunning}
            className={`px-6 py-3 rounded-xl text-sm font-bold border transition-all hover-lift flex items-center gap-2 mx-auto ${isRunning
              ? 'bg-white/[0.03] text-white/80 border-white/[0.06] cursor-wait'
              : 'bg-emerald-400/10 text-emerald-300 border-emerald-400/20 hover:bg-emerald-400/20'}`}
          >
            <BarChart3 className="w-4 h-4" />
            {isRunning ? 'Running Comparison...' : isDemo ? 'View Demo Comparison' : 'Run Full Comparison'}
          </button>
        </div>
      ) : isRunning ? (
        <div className="glass-card rounded-2xl p-10 flex flex-col items-center gap-4">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full bg-emerald-400/10 animate-ping" style={{ animationDuration: '2s' }} />
            <div className="relative w-full h-full bg-black border-2 border-emerald-400/20 rounded-full flex items-center justify-center">
              <BarChart3 className="w-7 h-7 text-emerald-400/60 animate-pulse" />
            </div>
          </div>
          <p className="text-sm text-white/90 text-center">Scoring across {data?.models?.length ?? 4} models with demographic mutations…</p>
        </div>
      ) : (
        <div className="glass-card rounded-2xl overflow-hidden">
          {/* Summary header */}
          <div className="px-5 py-4 border-b border-white/[0.06]">
            <div className="flex items-center gap-3 flex-wrap mb-2">
              {data.systemic_bias_detected && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-red-400/10 border border-red-400/20 text-red-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Systemic Bias Detected
                </span>
              )}
              <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-400/10 border border-emerald-400/20 text-emerald-400 flex items-center gap-1">
                <Shield className="w-3 h-3" /> Aethel Advantage: +{data.fairai_advantage_avg} pts avg
              </span>
              <span className="text-xs text-white/80 ml-auto">σ = {data.cross_model_variance} across models</span>
            </div>
            <p className="text-xs text-white/90 leading-relaxed">{data.summary}</p>
          </div>

          <div className="p-5">
            <AggregateBanner data={data} />

            {/* Tab switcher */}
            <div className="flex gap-1 mb-5 bg-white/[0.03] rounded-xl p-1 border border-white/[0.06]">
              {[{ id: 'cards', label: 'Model Cards' }, { id: 'table', label: 'Bias Matrix' }].map(t => (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${activeTab === t.id ? 'bg-white/[0.08] text-white' : 'text-white/80 hover:text-white'}`}>
                  {t.label}
                </button>
              ))}
            </div>

            {activeTab === 'cards' && (
              <div className="space-y-3">
                {/* Own model first */}
                {fairaiModel && <ModelCard model={fairaiModel} fairaiScore={fairaiModel.score} isOwnModel={true} />}
                {/* Other models */}
                {otherModels.map((m, i) => (
                  <ModelCard key={i} model={m} fairaiScore={fairaiModel?.score ?? 70} isOwnModel={false} />
                ))}
              </div>
            )}

            {activeTab === 'table' && (
              <div className="rounded-xl border border-white/[0.08] overflow-hidden">
                <BiasVerdictTable models={data.models ?? []} />
              </div>
            )}

            {/* Insight footer */}
            {data.insight && (
              <div className="mt-5 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-3">
                <Zap className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <p className="text-xs text-white/90 leading-relaxed">{data.insight}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
