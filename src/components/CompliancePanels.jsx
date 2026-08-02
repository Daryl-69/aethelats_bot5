import React, { useState } from 'react';
import { Zap, Shield, Lock, CheckCircle, XCircle, Cpu, BookOpen, ChevronRight, ChevronUp, ChevronDown, GitBranch, AlertTriangle, FileText, Brain, Network, BarChart2, Beaker, CheckSquare } from 'lucide-react';
import { SectionHeading, AnimatedBar } from './UIHelpers';

export function FeatureAttributionChart({ attributions, fitScore }) {
  if (!attributions || attributions.length === 0) return null;
  const sorted = [...attributions].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  const maxAbs = Math.max(...sorted.map(a => Math.abs(a.delta)), 1);
  return (
    <section className="mb-6 animate-fade-in-up stagger-2">
      <SectionHeading icon={<Zap className="w-3.5 h-3.5" />} label="Score Attribution — Why This Score?" />
      <div className="glass-card glass-card-hover rounded-2xl p-6">
        <div className="space-y-2.5">{sorted.map((attr, i) => {
          const isPos = attr.delta >= 0;
          const w = Math.round((Math.abs(attr.delta) / maxAbs) * 100);
          return (
            <div key={i} className="group hover-lift rounded-lg p-2 -mx-2">
              <div className="flex items-center gap-3">
                <div className={'w-12 text-right text-sm font-black shrink-0 ' + (isPos ? 'text-white' : 'text-white/90')}>{isPos ? '+' : ''}{attr.delta}</div>
                <div className="flex-1"><div className="h-5 flex items-center">
                  <div className={'h-4 rounded-md transition-all duration-700 ' + (isPos ? 'bg-white/30' : 'bg-white/10')} style={{ width: w + '%', minWidth: '8px', animation: 'barFill 1s ease-out forwards', animationDelay: (i * 0.1) + 's' }} />
                </div></div>
                <div className="w-2/5 min-w-0 shrink-0"><div className="text-xs font-semibold text-white truncate">{attr.factor}</div></div>
              </div>
              <div className="ml-16 pl-1 text-xs text-white mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity">{attr.reasoning}</div>
            </div>
          );
        })}</div>
        <div className="mt-5 pt-4 border-t border-white/[0.06] flex items-center justify-end gap-4">
          <span className="text-xs text-white/80">Net score</span>
          <span className="text-3xl font-black text-white">{fitScore}<span className="text-sm text-white/80 font-normal ml-1">/ 100</span></span>
        </div>
      </div>
    </section>
  );
}

export function FairnessMetricsCard({ metrics }) {
  if (!metrics) return null;
  const grade = metrics.overall_grade || 'C';
  return (
    <section className="mb-6 animate-fade-in-up stagger-8">
      <SectionHeading icon={<Shield className="w-3.5 h-3.5" />} label="Fairness Metrics — Report Card" />
      <div className="glass-card glass-card-hover rounded-2xl overflow-hidden">
        <div className="px-6 py-5 border-b border-white/[0.06] flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl border-2 border-white/20 flex items-center justify-center shrink-0 bg-white/[0.05]">
            <span className="text-3xl font-black text-white">{grade}</span>
          </div>
          <div>
            <div className="text-base font-bold text-white mb-1">Grade: {grade} <span className="text-sm font-normal text-white/90">— {metrics.passing_count}/{metrics.total_count} passing</span></div>
            <p className="text-xs text-white/80 leading-relaxed">Based on EEOC, EU AI Act, and NYC Local Law 144.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-white/[0.03]">{(metrics.metrics || []).map((m, i) => (
          <div key={i} className="p-5 bg-[#0a0a0a] hover:bg-white/[0.02] transition-colors">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2"><span className={'w-2 h-2 rounded-full ' + (m.passes ? 'bg-[#22c55e]' : 'bg-[#ef4444]')} /><span className="text-xs font-bold text-white uppercase tracking-wider">{m.label}</span></div>
              <span className={'px-2 py-0.5 rounded text-xs font-bold border ' + (m.passes ? 'bg-[#22c55e]/10 text-[#22c55e] border-[#22c55e]/20' : 'bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20')}>{m.passes ? '✓ PASS' : '✗ FAIL'}</span>
            </div>
            <div className="flex items-baseline gap-2 mb-1.5"><span className={'text-2xl font-black ' + (m.passes ? 'text-white' : 'text-white')}>{m.display}</span><span className="text-xs text-white/80">{m.direction === 'gte' ? '≥' : '≤'} {m.threshold}</span></div>
            <span className="text-xs px-1.5 py-0.5 rounded bg-white/[0.04] text-white/80 border border-white/[0.06]">{m.regulation}</span>
          </div>
        ))}</div>
      </div>
    </section>
  );
}

export function ComplianceDashboard({ result, cfResult }) {
  const checks = [
    { regulation: 'EU AI Act Art. 10', requirement: 'Data governance & bias monitoring', feature: 'PII Stripping + Bias Proxy Detection', met: !!(result?.pii_removed) },
    { regulation: 'EU AI Act Art. 13', requirement: 'Transparency & information', feature: 'Score attribution & full reasoning', met: !!(result?.feature_attributions?.length > 0) },
    { regulation: 'EU AI Act Art. 14', requirement: 'Human oversight', feature: 'Fairness Gate — mandatory review', met: true },
    { regulation: 'EU AI Act Art. 9', requirement: 'Risk management', feature: 'Bias Stability + Metrics', met: !!cfResult },
    { regulation: 'EEOC 4/5ths Rule', requirement: 'Disparate impact ≥ 0.80', feature: 'Disparate Impact Ratio', met: !!cfResult?.fairness_metrics },
    { regulation: 'NYC Local Law 144', requirement: 'Bias audit of hiring tools', feature: 'Counterfactual mutation testing', met: !!cfResult },
    { regulation: 'GDPR Art. 22', requirement: 'Right to explanation', feature: 'Feature attribution chart', met: !!(result?.feature_attributions?.length > 0) },
  ];
  const passed = checks.filter(c => c.met).length;
  return (
    <section className="mb-6 animate-fade-in-up stagger-8">
      <SectionHeading icon={<Lock className="w-3.5 h-3.5" />} label="Regulatory Compliance" />
      <div className="glass-card glass-card-hover rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="text-sm font-bold text-white">{passed}/{checks.length} met</div>
            <div className="h-2 w-32 bg-white/[0.06] rounded-full overflow-hidden"><div className="h-full rounded-full bg-white/40 transition-all" style={{ width: (passed / checks.length * 100) + '%' }} /></div>
          </div>
        </div>
        <div className="divide-y divide-white/[0.04]">{checks.map((c, i) => (
          <div key={i} className="grid grid-cols-12 gap-3 px-5 py-3 items-center hover:bg-white/[0.02] transition-colors">
            <div className="col-span-1 flex justify-center">{c.met ? <CheckCircle className="w-4 h-4 text-white" /> : <XCircle className="w-4 h-4 text-white" />}</div>
            <div className="col-span-3"><span className="text-xs font-bold text-white">{c.regulation}</span></div>
            <div className="col-span-4"><span className="text-xs text-white/90">{c.requirement}</span></div>
            <div className="col-span-4"><span className={'text-xs ' + (c.met ? 'text-white/80' : 'text-white italic')}>{c.met ? c.feature : 'Run all stages'}</span></div>
          </div>
        ))}</div>
      </div>
    </section>
  );
}

export function MultiModelComparison({ mmResult, isRunning, onRunTest, isDemo }) {
  const data = mmResult;
  const globalMax = data ? Math.max(...data.model_results.map(m => m.max_delta), 1) : 1;
  const deltaColor = (d) => d > 5 ? 'text-white' : d > 2 ? 'text-white' : 'text-white/90';
  return (
    <section className="mb-6 animate-fade-in-up stagger-8">
      <SectionHeading icon={<Cpu className="w-3.5 h-3.5" />} label="Multi-Model Cross-Examination" />
      {!data ? (
        <div className="glass-card glass-card-hover rounded-2xl p-6 text-center">
          <p className="text-sm text-white/90 mb-4">Score with 3 LLMs to prove bias is systemic.</p>
          <button onClick={onRunTest} disabled={isRunning} className={'px-5 py-2.5 rounded-xl text-sm font-semibold border transition-all hover-lift ' + (isRunning ? 'bg-white/[0.03] text-white/80 border-white/[0.06] cursor-wait' : 'bg-white/[0.06] text-white border-white/10 hover:bg-white/[0.1]')}>
            {isRunning ? 'Testing...' : 'Run Comparison'}
          </button>
        </div>
      ) : (
        <div className="glass-card glass-card-hover rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.06]">
            <div className="flex items-center gap-3 flex-wrap">
              {data.systemic_bias_detected && <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white/[0.06] text-white border border-white/10">⚠ Systemic Bias</span>}
              <span className="text-xs text-white/80">σ = {data.cross_model_variance} · Avg institution bias = +{data.avg_institution_bias}</span>
            </div>
            <p className="text-xs text-white/90 mt-2 leading-relaxed">{data.summary}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-white/[0.06] text-white/80">
                <th className="text-left px-5 py-3 font-bold uppercase tracking-wider">Model</th>
                <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Score</th>
                <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Inst. Δ</th>
                <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Gap Δ</th>
                <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Name Δ</th>
                <th className="text-center px-3 py-3 font-bold uppercase tracking-wider">Max</th>
              </tr></thead>
              <tbody className="divide-y divide-white/[0.04]">{data.model_results.map((m, i) => (
                <tr key={i} className={'hover:bg-white/[0.02] transition-colors animate-table-row ' + (m.max_delta > 8 ? 'table-row-flagged' : '')} style={{ animationDelay: (i * 0.15) + 's' }}>
                  <td className="px-5 py-4"><div className="font-bold text-white">{m.model_label}</div><div className="text-white/80 mt-0.5 truncate max-w-[200px]">{m.reason}</div></td>
                  <td className="text-center px-3 py-4"><span className="text-lg font-black text-white">{m.original_score}</span></td>
                  {['institution_delta', 'gap_delta', 'name_delta'].map(key => {
                    const d = m[key]; const w = globalMax > 0 ? Math.round((Math.abs(d) / globalMax) * 100) : 0;
                    const barC = Math.abs(d) > 5 ? 'bg-white/40' : Math.abs(d) > 2 ? 'bg-white/25' : 'bg-white/15';
                    return (
                      <td key={key} className="px-3 py-4"><div className="flex items-center gap-2 justify-center">
                        <span className={'font-black ' + deltaColor(Math.abs(d))}>{d >= 0 ? '+' : ''}{d}</span>
                        <div className="w-16 h-2 bg-white/[0.06] rounded-full overflow-hidden"><div className={'h-full rounded-full ' + barC} style={{ width: Math.max(w, 6) + '%' }} /></div>
                      </div></td>
                    );
                  })}
                  <td className="text-center px-3 py-4"><span className={'text-sm font-black px-2 py-0.5 rounded ' + (m.max_delta > 5 ? 'bg-white/10 text-white' : 'bg-white/[0.05] text-white')}>{m.max_delta}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

export function ResearchCitationsSection() {
  const [open, setOpen] = useState(false);
  const citations = [
    { feature: 'PII Stripping', authors: 'Bertrand & Mullainathan (2004)', title: 'Are Emily and Greg More Employable...', journal: 'American Economic Review', finding: 'White-sounding names received 50% more callbacks.' },
    { feature: 'Institution Bias', authors: 'Rivera (2015)', title: 'Pedigree: How Elite Students Get Elite Jobs', journal: 'Princeton University Press', finding: 'Evaluators preferred elite university candidates with identical skills.' },
    { feature: 'Career Gap', authors: 'Weisshaar (2018)', title: 'From Opt Out to Blocked Out', journal: 'American Sociological Review', finding: 'Employment gaps reduced callbacks by 45.4%.' },
    { feature: 'JD Language', authors: 'Gaucher et al. (2011)', title: 'Evidence That Gendered Wording Exists', journal: 'J. Personality and Social Psychology', finding: 'Masculine-coded ads reduced women\'s interest.' },
  ];
  return (
    <section className="mb-6">
      <div className="rounded-2xl border border-white/[0.06] glass-card glass-card-hover overflow-hidden">
        <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-white/[0.03] transition-colors">
          <BookOpen className="w-5 h-5 text-white/80 shrink-0" />
          <div className="flex-1"><div className="text-sm font-semibold text-white">Research & Methodology</div></div>
          {open ? <ChevronUp className="w-4 h-4 text-white/80" /> : <ChevronDown className="w-4 h-4 text-white/80" />}
        </button>
        {open && (
          <div className="px-5 pb-5 border-t border-white/[0.06] space-y-3 pt-4">{citations.map((c, i) => (
            <div key={i} className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4">
              <div className="flex items-start gap-3">
                <span className="text-xs px-2 py-0.5 rounded bg-white/[0.05] text-white/90 border border-white/[0.06] shrink-0 mt-0.5">{c.feature}</span>
                <div><div className="text-xs font-semibold text-white">{c.authors}</div><div className="text-xs text-white/80 italic mt-0.5">"{c.title}"</div><div className="text-xs text-white/90 mt-1.5"><strong>Finding:</strong> {c.finding}</div></div>
              </div>
            </div>
          ))}</div>
        )}
      </div>
    </section>
  );
}

export function ArchitectureDiagram() {
  const stages = [
    { icon: <FileText className="w-5 h-5 text-white" />, label: 'Resume\nUpload' },
    { icon: <Lock className="w-5 h-5 text-white" />, label: 'PII\nStrip' },
    { icon: <Brain className="w-5 h-5 text-emerald-400" />, label: 'Blind\nScore' },
    { icon: <Network className="w-5 h-5 text-white" />, label: 'Skill\nGraph' },
    { icon: <AlertTriangle className="w-5 h-5 text-yellow-400" />, label: 'Bias\nDetect' },
    { icon: <BarChart2 className="w-5 h-5 text-white" />, label: 'Percentile\nRank' },
    { icon: <Beaker className="w-5 h-5 text-emerald-400" />, label: 'Counter-\nfactual' },
    { icon: <CheckSquare className="w-5 h-5 text-white" />, label: 'Fairness\nGate' },
  ];
  return (
    <div className="mt-6 rounded-2xl border border-white/[0.06] glass-card glass-card-hover p-5 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 blur-[100px] pointer-events-none" />
      <div className="flex items-center gap-2 mb-8 relative z-10"><GitBranch className="w-4 h-4 text-white/80" /><span className="text-xs font-bold uppercase tracking-[0.15em] text-white">8-Stage Pipeline</span></div>
      
      <div className="flex items-center gap-6 overflow-x-auto pb-6 relative z-10 px-2 scene">
        {stages.map((s, i) => (
          <React.Fragment key={i}>
            <div className="flex flex-col items-center shrink-0 group cursor-default">
              
              {/* 3D CSS Cube */}
              <div className="cube mb-8">
                <div className="cube-core" />
                <div className="cube-face cube-face-front">{s.icon}</div>
                <div className="cube-face cube-face-back"></div>
                <div className="cube-face cube-face-right"></div>
                <div className="cube-face cube-face-left"></div>
                <div className="cube-face cube-face-top"></div>
                <div className="cube-face cube-face-bottom"></div>
              </div>

              <div className="text-[10px] text-white/90 group-hover:text-white text-center whitespace-pre-line leading-tight font-bold transition-colors duration-500">
                {s.label}
              </div>
            </div>
            {i < stages.length - 1 && <ChevronRight className="w-4 h-4 text-white/10 shrink-0 mb-8" />}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
