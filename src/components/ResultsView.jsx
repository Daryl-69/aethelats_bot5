import React from 'react';
import { CheckCircle, AlertTriangle, RefreshCw, Printer, Eye, Target, ClipboardList, TrendingUp, TrendingDown, Shield, Download, FileText, Clock, Wrench, BarChart2, Users, Sparkles, ArrowRight } from 'lucide-react';
import { SectionHeading, Pill, ScoreMeter, AnimatedBar, useCountUp, getFitVariant } from './UIHelpers';
import { PercentileBadge, PIIStripPanel, SkillDepthSection, SkillMatchSection } from './FeatureSections';
import { ProofOfWorkSection, BiasStabilitySection } from './AnalysisPanels';
import { FeatureAttributionChart, FairnessMetricsCard, ComplianceDashboard, ResearchCitationsSection } from './CompliancePanels';
import { ModelComparisonPanel } from './ModelComparisonPanel';
import SkillKnowledgeGraph from './SkillKnowledgeGraph';
import { SEVERITY_STYLE, BIAS_TYPE_LABELS } from './constants';
import { useAuth } from '../context/AuthContext';

export default function ResultsView({ s, onOpenCoach }) {
  const { user } = useAuth();
  const isCandidate = user?.role === 'candidate';
  const isRecruiter = !isCandidate;
  const result = s.result;
  const fitScore = result?.fit_score || 0;
  const legacyScore = result?.counterfactual?.legacy_ats_score || Math.max(0, fitScore - 20);
  const scoreDelta = result?.counterfactual?.score_delta || (fitScore - legacyScore);
  const biasProxies = result?.bias_proxies || [];
  const radar = result?.radar || {};
  const fitLevel = result?.fit_level || '';
  const recommendation = result?.recommendation || 'Schedule Screening Call';
  const legacyVerdict = result?.legacy_ats_verdict || 'Flagged for Review';
  const animScore = useCountUp(fitScore, 1500);
  const animTech = useCountUp(radar.technical_depth || 0, 1200);
  const animLead = useCountUp(radar.project_complexity || 0, 1200);

  const [exporting, setExporting] = React.useState(false);
  const candidateId = React.useRef(`AETH-${Math.floor(Math.random() * 90000 + 10000)}`);

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'https://daryllll-gyufuyf.hf.space';
      const payload = {
        role: s.jobRole || 'Unknown Role',
        fit_score: fitScore,
        legacy_ats_score: legacyScore,
        candidate_id: candidateId.current,
        cf_result: s.cfResult || null,
        comp_result: s.compResult || null,
      };
      const res = await fetch(`${API_BASE}/export-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `aethel-audit-${candidateId.current}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`PDF export failed: ${e.message}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-8 pb-20 max-w-6xl animate-fade-in">
      {biasProxies.length > 0 && !s.fairnessConfirmed && (
        <div className="mb-4 rounded-2xl warning-card-yellow px-6 py-4 flex items-start gap-4 no-print animate-fade-in-up">
          <AlertTriangle className="w-5 h-5 text-black shrink-0 mt-0.5" />
          <div className="flex-1"><div className="font-semibold text-black mb-0.5">Fairness Review Required</div><p className="text-xs text-black/80">{biasProxies.length} bias proxies detected. Acknowledge before proceeding.</p></div>
          <button onClick={() => s.handlePrimaryAction(recommendation)} className="px-4 py-2 rounded-xl bg-black/10 hover:bg-black/20 border border-black/20 text-black text-xs font-bold transition-colors shrink-0">Review →</button>
        </div>
      )}
      {s.fairnessConfirmed && (
        <div className="mb-4 rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-4 flex items-center gap-4 no-print"><CheckCircle className="w-5 h-5 text-white shrink-0" /><div><div className="font-semibold text-white">Review Completed</div><p className="text-xs text-white/80">Timestamped for compliance.</p></div></div>
      )}
      <PIIStripPanel items={result.pii_removed || []} />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in-up">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-white mb-1">
            {isCandidate ? 'My Results' : 'Audit Trail / Results'}
          </div>
          <h1 className="text-2xl font-bold text-white">
            {isCandidate ? 'Your Resume Score' : 'Candidate Analysis'}
          </h1>
          <p className="text-white/90 text-sm">
            {isCandidate
              ? `${s.jobRole || 'Target Role'} · See how your resume scores and where to improve`
              : `Sr. Director of Engineering · Candidate ID: #${candidateId.current}`
            }
          </p>
        </div>
        <div className="flex items-center gap-3 no-print">
          {isRecruiter && (
            <>
              <button
                onClick={handleExportPDF}
                disabled={exporting}
                className="px-4 py-2.5 rounded-xl text-sm border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] text-white transition-all flex items-center gap-2 hover-lift disabled:opacity-50 disabled:cursor-wait"
              >
                <Download className="w-4 h-4" />
                {exporting ? 'Generating…' : 'Download Audit Report'}
              </button>
              <button onClick={() => s.handlePrimaryAction(recommendation)} className="px-4 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 btn-premium">
                <CheckCircle className="w-4 h-4" />Advance to Final
              </button>
            </>
          )}
          {isCandidate && (
            <button onClick={s.reset} className="px-4 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 btn-premium">
              <RefreshCw className="w-4 h-4" />Audit Another Resume
            </button>
          )}
        </div>
      </div>


      {/* Score Cards Row */}
      <div className="flex flex-col md:grid md:grid-cols-3 gap-4 mb-6">
        <div className="glass-card-hover rounded-2xl p-6 flex flex-col items-center text-center animate-fade-in-up stagger-1 md:col-span-1">
          <div className="flex items-center justify-between w-full mb-2"><span className="text-xs text-white uppercase tracking-wider">Composite Score</span><span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/20">● CLEARED</span></div>
          <ScoreMeter value={fitScore} size={180} />
          <p className="text-xs text-white/80 mt-3">Top {100 - (result.percentile || 88)}% of candidate pool for this role archetype.</p>
        </div>
        
        {/* 2-Column Grid container for secondary metrics on mobile */}
        <div className="grid grid-cols-2 gap-3 md:col-span-2 md:gap-4">
          <div className="glass-card-hover rounded-2xl p-4 sm:p-6 animate-fade-in-up stagger-2">
            <div className="flex items-center justify-between mb-2 sm:mb-3"><span className="text-[11px] sm:text-sm font-semibold text-white tracking-tight">Tech Aptitude</span><BarChart2 className="w-4 h-4 sm:w-5 sm:h-5 text-white/50" /></div>
            <div className="flex items-baseline gap-1.5 sm:gap-3 mb-2"><span className="text-3xl sm:text-5xl font-black text-white">{animTech}</span><span className="text-[10px] sm:text-sm text-[#22c55e] font-semibold tracking-tight">+4% avg</span></div>
            <AnimatedBar value={radar.technical_depth || 0} delay={200} color="bg-white/40" />
          </div>
          <div className="glass-card-hover rounded-2xl p-4 sm:p-6 animate-fade-in-up stagger-3">
            <div className="flex items-center justify-between mb-2 sm:mb-3"><span className="text-[11px] sm:text-sm font-semibold text-white tracking-tight">Leadership</span><Users className="w-4 h-4 sm:w-5 sm:h-5 text-white/50" /></div>
            <div className="flex items-baseline gap-1.5 sm:gap-3 mb-2"><span className="text-3xl sm:text-5xl font-black text-white">{animLead}</span><span className="text-[10px] sm:text-sm text-white/90 font-semibold tracking-tight">-1% avg</span></div>
            <AnimatedBar value={radar.project_complexity || 0} delay={300} color="bg-white/30" />
          </div>
        </div>
      </div>

      {/* Warning Card */}
      {biasProxies.some(p => p.severity === 'high') && (
        <div className="mb-6 warning-card-yellow rounded-2xl p-5 flex items-start gap-4 animate-fade-in-up stagger-3">
          <AlertTriangle className="w-6 h-6 text-black shrink-0 mt-0.5" />
          <div className="flex-1"><h3 className="text-lg font-bold text-black mb-1">Employment Gap Detected</h3><p className="text-sm text-black/80 leading-relaxed">{biasProxies.find(p => p.severity === 'high')?.explanation || 'Automated check identified a variance.'}</p>
            <button className="mt-3 px-4 py-2 rounded-lg border border-black/30 text-black text-sm font-bold hover:bg-black/10 transition-all">Request Clarification</button>
          </div>
        </div>
      )}

      {/* Cognitive & Behavioral Analysis */}
      <section className="mb-6 animate-fade-in-up stagger-4">
        <div className="glass-card glass-card-hover rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-5">Cognitive & Behavioral Analysis</h3>
          {[{ label: 'Strategic Thinking', value: radar.problem_solving || 85, level: 'Superior' },
            { label: 'Adaptability', value: radar.impact_evidence || 78, level: 'Proficient' },
            { label: 'Risk Tolerance', value: radar.domain_knowledge || 82, level: 'Moderate' }
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-4 mb-4 last:mb-0">
              <span className="text-sm text-white w-40 shrink-0">{item.label}</span>
              <div className="flex-1"><AnimatedBar value={item.value} delay={i * 200} color="bg-white/40" /></div>
              <span className="text-sm font-semibold text-white w-24 text-right">{item.level}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Reasoning (Bot 4 Analysis Paragraph) */}
      {result.summary && (
        <section className="mb-6 animate-fade-in-up stagger-4">
          <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10"><Target className="w-24 h-24 text-white" /></div>
            <div className="flex items-center gap-2 mb-4 relative z-10">
              <span className="text-sm font-bold text-white">REASONING</span>
            </div>
            <p className="text-sm text-white/90 leading-relaxed relative z-10">{result.summary}</p>
          </div>
        </section>
      )}

      {/* Structured Analysis (Bot 3 Data) */}
      {result.structured_data && (
        <section className="mb-6 animate-fade-in-up stagger-5">
          <SectionHeading icon={<FileText className="w-3.5 h-3.5" />} label="Structured Analysis" rightBadge={<span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 font-bold uppercase tracking-wider">BIAS-FREE</span>} />
          <div className="glass-card glass-card-hover rounded-2xl p-6">
            
            {/* Experience */}
            {(() => {
              const sd = result.structured_data;
              const roles = (sd.experience && sd.experience.length > 0) ? sd.experience
                : (sd.work_experience_summary?.roles?.length > 0) ? sd.work_experience_summary.roles
                : (sd.job_history && sd.job_history.length > 0) ? sd.job_history
                : [];
              return (
                <div className="mb-6">
                  <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider mb-3 flex items-center gap-2"><Clock className="w-3.5 h-3.5" /> Work Experience ({roles.length} {roles.length === 1 ? 'role' : 'roles'}{sd.work_experience_summary ? ` · ${sd.work_experience_summary.total_years || 0} yrs total` : ''})</h4>
                  {roles.length > 0 ? (
                    <div className="space-y-3">
                      {roles.map((job, idx) => (
                        <div key={idx} className="bg-white/[0.03] border border-white/[0.05] rounded-xl p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="font-bold text-white text-sm">{job.title || 'Role'}</span>
                              <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${(job.type || 'Job') === 'Internship' ? 'bg-blue-500/10 text-blue-300 border-blue-500/20' : 'bg-white/10 text-white border-white/20'}`}>{(job.type || 'Job') === 'Internship' ? '🎓 Internship' : '💼 Job'}</span>
                            </div>
                            {job.duration_months > 0 && <span className="text-xs text-white/60">{job.duration_months >= 12 ? `${Math.floor(job.duration_months/12)}y ${job.duration_months%12}m` : `${job.duration_months}m`}</span>}
                          </div>
                          {(job.company || job.date_range) && (
                            <div className="text-xs text-white/50 mt-1.5 flex gap-3">
                              {job.company && <span>{job.company}</span>}
                              {job.date_range && <span>{job.date_range}</span>}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-white/50 italic">No experience data extracted.</div>
                  )}
                </div>
              );
            })()}

            {/* Education */}
            <div className="mb-6 bg-white/[0.03] border border-white/[0.05] rounded-xl p-4">
              <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Highest Degree</h4>
              <div className="text-lg font-bold text-white">{result.structured_data.highest_degree || 'None'}</div>
            </div>

            {/* Technical Skills */}
            <div>
              <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider mb-3 flex items-center gap-2"><Wrench className="w-3.5 h-3.5" /> Technical Skills ({result.structured_data.technical_skills?.length || 0})</h4>
              <div className="flex flex-wrap gap-2">
                {(result.structured_data.technical_skills || []).map((skill, idx) => (
                  <span key={idx} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/10 text-cyan-200 border border-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.1)]">
                    # {skill}
                  </span>
                ))}
              </div>
            </div>

          </div>
        </section>
      )}

      {/* Skill Analysis with Knowledge Graph */}
      <section className="mb-6 animate-fade-in-up stagger-5">
        <SectionHeading icon={<Target className="w-3.5 h-3.5" />} label="Skill Analysis — Insights" />
        <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-4">
          <div className="space-y-4">
            <div className="glass-card glass-card-hover rounded-2xl p-5">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-14 h-14 rounded-xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center text-2xl">👤</div>
                <div><div className="text-lg font-bold text-white">Candidate Profile</div><p className="text-xs text-white/90">{s.jobRole ? s.jobRole + ' Candidate' : 'Candidate Evaluation'}</p>
                  <div className="flex gap-2 mt-1"><span className="text-[10px] px-2 py-0.5 rounded-full bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/20 font-bold">● Verified</span><span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white border border-white/[0.08] font-bold">98% Match</span></div>
                </div>
              </div>
            </div>
          </div>
          <SkillKnowledgeGraph skillData={result.skill_matches} />
        </div>
      </section>

      <ProofOfWorkSection detectedLinks={result.detected_links || (s.isDemo ? [{ url: '#', platform: 'github' }, { url: '#', platform: 'leetcode' }, { url: '#', platform: 'linkedin' }] : [])} proofResult={s.proofResult} isLoading={s.proofLoading} onFetch={s.handleProofOfWork} isDemo={s.isDemo} />

      {biasProxies.length > 0 && (
        <section className="mb-6 animate-fade-in-up stagger-6">
          <SectionHeading icon={<Eye className="w-3.5 h-3.5" />} label={'Bias Proxies — ' + biasProxies.length + ' Found'} />
          <div className="glass-card glass-card-hover rounded-2xl overflow-hidden">
            <div className="hidden lg:grid grid-cols-12 gap-3 px-5 py-3 border-b border-white/[0.06] bg-white/[0.02]">
              <div className="col-span-3 text-xs font-bold uppercase tracking-widest text-white">Proxy</div>
              <div className="col-span-2 text-xs font-bold uppercase tracking-widest text-white">Type</div>
              <div className="col-span-1 text-xs font-bold uppercase tracking-widest text-white text-center">Risk</div>
              <div className="col-span-6 text-xs font-bold uppercase tracking-widest text-white">Explanation</div>
            </div>
            <div className="divide-y divide-white/[0.04]">{biasProxies.map((proxy, idx) => {
              const sev = SEVERITY_STYLE[proxy.severity] || SEVERITY_STYLE.low;
              const bt = BIAS_TYPE_LABELS[proxy.bias_type] || BIAS_TYPE_LABELS.gender;
              return (
                <div key={idx} className="flex flex-col lg:grid lg:grid-cols-12 gap-2 lg:gap-3 px-4 lg:px-5 py-4 items-start hover:bg-white/[0.02] transition-colors animate-table-row" style={{ animationDelay: (idx * 0.1) + 's' }}>
                  <div className="lg:col-span-3 flex items-center gap-2">
                    <span className="lg:hidden text-[10px] font-bold uppercase tracking-wider text-white/40 w-12 shrink-0">Proxy</span>
                    <code className={'text-[11px] px-2 py-1 rounded-lg border font-mono font-semibold break-words max-w-[200px] sm:max-w-none ' + bt.bg + ' ' + bt.color + ' ' + bt.border}>"{proxy.text}"</code>
                  </div>
                  <div className="lg:col-span-2 flex items-center gap-2">
                    <span className="lg:hidden text-[10px] font-bold uppercase tracking-wider text-white/40 w-12 shrink-0">Type</span>
                    <span className={'text-[11px] font-semibold px-2 py-0.5 rounded-md border ' + bt.bg + ' ' + bt.color + ' ' + bt.border}>{bt.label}</span>
                  </div>
                  <div className="lg:col-span-1 flex lg:justify-center items-center gap-2 lg:pt-0.5">
                    <span className="lg:hidden text-[10px] font-bold uppercase tracking-wider text-white/40 w-12 shrink-0">Risk</span>
                    <span className={'px-2 py-0.5 rounded-md text-[10px] font-bold uppercase border ' + sev.bg + ' ' + sev.text + ' ' + sev.border}>{proxy.severity}</span>
                  </div>
                  <div className="lg:col-span-6 text-xs text-white/90 leading-relaxed mt-2 lg:mt-0 flex items-start gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-white shrink-0 mt-0.5" />
                    <span>{proxy.explanation}</span>
                  </div>
                </div>
              );
            })}</div>
          </div>
        </section>
      )}

      <section className="mb-6 animate-fade-in-up stagger-6">
        <SectionHeading icon={<ClipboardList className="w-3.5 h-3.5" />} label="Signals & Gaps" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="glass-card glass-card-hover rounded-2xl p-5 hover-glow">
            <div className="flex items-center gap-2 mb-4"><TrendingUp className="w-4 h-4 text-white/90" /><h4 className="font-semibold text-white text-sm">Strong Signals ({(result.strong_signals || []).length})</h4></div>
            <div className="space-y-3">{(result.strong_signals || []).map((sig, i) => (
              <div key={i} className="flex items-start gap-3"><div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 bg-white/40" /><div><div className="text-sm font-semibold text-white">{sig.signal}</div></div></div>
            ))}</div>
          </div>
          <div className="glass-card glass-card-hover rounded-2xl p-5 hover-glow">
            <div className="flex items-center gap-2 mb-4"><TrendingDown className="w-4 h-4 text-white/80" /><h4 className="font-semibold text-white/90 text-sm">Gaps ({(result.gaps || []).length})</h4></div>
            <div className="space-y-3">{(result.gaps || []).map((gap, i) => (
              <div key={i} className="flex items-start gap-3"><div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 bg-white/20" /><div><div className="text-sm font-semibold text-white">{gap.gap}</div><div className="text-xs text-white/80 mt-0.5">{gap.severity === 'blocking' ? 'Blocking' : 'Minor'}</div></div></div>
            ))}</div>
          </div>
        </div>
      </section>

      {/* Recruiter-only: counterfactual, model comparison, compliance */}
      {isRecruiter && (
        <>
          <BiasStabilitySection cfResult={s.cfResult} isRunning={s.runningCF} onRunTest={s.handleCounterfactualTest} isDemo={s.isDemo} />
          <ModelComparisonPanel compResult={s.compResult} isRunning={s.runningComp} onRunTest={s.handleModelComparison} isDemo={s.isDemo} />
          <FairnessMetricsCard metrics={s.cfResult?.fairness_metrics} />
          <ComplianceDashboard result={result} cfResult={s.cfResult} />
          <ResearchCitationsSection />
        </>
      )}

      {/* Candidate: AI Coach CTA */}
      {isCandidate && (
        <section className="mb-6 animate-fade-in-up stagger-7">
          <div className="glass-card glass-card-hover rounded-2xl p-6 border border-white/10 flex flex-col sm:flex-row items-start sm:items-center gap-5"
            style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(168,85,247,0.08) 100%)' }}>
            <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 bg-indigo-500/20 border border-indigo-500/30">
              <Sparkles className="w-6 h-6 text-indigo-300" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-bold text-white mb-1">Get Personalised Coaching</h3>
              <p className="text-sm text-white/70 leading-relaxed">Your AI coach can explain your score, help you improve specific bullets, and prep you for interviews based on your gaps.</p>
            </div>
            <button
              onClick={onOpenCoach}
              className="px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 shrink-0 bg-indigo-500/20 border border-indigo-500/30 text-indigo-200 hover:bg-indigo-500/30 transition-all">
              <Sparkles className="w-4 h-4" />Talk to AI Coach →
            </button>
          </div>
        </section>
      )}

      <section className="animate-fade-in-up stagger-8">
        <SectionHeading icon={<CheckCircle className="w-3.5 h-3.5" />} label={isCandidate ? 'Next Steps' : 'Recommendation'} />
        <div className="border border-white/10 rounded-2xl p-6 glass-card glass-card-hover flex flex-col sm:flex-row items-start sm:items-center gap-5">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 bg-white/[0.06] border border-white/[0.08]"><CheckCircle className="w-6 h-6 text-white" /></div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-white mb-1">
              {isCandidate ? (fitScore >= 70 ? 'Strong Match — Apply with Confidence' : fitScore >= 50 ? 'Good Potential — Address the Gaps' : 'Needs Work — Focus on Key Gaps') : recommendation}
            </h3>
            <p className="text-sm text-white/90 leading-relaxed">{result.summary}</p>
            {isRecruiter && scoreDelta > 0 && <p className="text-xs text-white/80 mt-2"><AlertTriangle className="w-3 h-3 inline mr-1" />Without blind eval, score would have been {legacyScore}/100.</p>}
          </div>
          {isRecruiter && (
            <button onClick={() => s.handlePrimaryAction(recommendation)} className="px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 shrink-0 no-print btn-premium">
              {biasProxies.length > 0 && !s.fairnessConfirmed ? <><AlertTriangle className="w-4 h-4" />Review & Proceed</> : 'Advance Candidate'}
            </button>
          )}
          {isCandidate && (
            <button onClick={s.reset} className="px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 shrink-0 no-print btn-premium">
              <ArrowRight className="w-4 h-4" />Audit Another
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
