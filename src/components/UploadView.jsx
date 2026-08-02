import React, { useEffect, useState } from 'react';
import { UploadCloud, FileText, XCircle, RefreshCw, Zap, Check, Play, AlertTriangle, Clock } from 'lucide-react';
import { ToggleSwitch } from './UIHelpers';
import { JDAnalysisSection } from './AnalysisPanels';
import { ArchitectureDiagram } from './CompliancePanels';
import { DEMO_JD_RESULT, API_URL } from './constants';
import { useAuth } from '../context/AuthContext';

function fmtTime(iso) {
  if (!iso) return '';
  const d   = new Date(iso);
  const now = new Date();
  const ms  = now - d;
  if (ms < 60000)          return 'just now';
  if (ms < 3600000)        return `${Math.floor(ms/60000)}m ago`;
  if (ms < 86400000)       return `${Math.floor(ms/3600000)}h ago`;
  return `${Math.floor(ms/86400000)}d ago`;
}

export default function UploadView({ s }) {
  const { user, authHeaders } = useAuth();
  const isCandidate = user?.role === 'candidate';
  const [recentScans, setRecentScans]   = useState([]);
  const [scansLoading, setScansLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/user/scans`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setRecentScans((data.scans || []).slice(0, 5)))
      .catch(() => {})
      .finally(() => setScansLoading(false));
  }, []);

  return (
    <div className="p-4 sm:p-8 animate-fade-in">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <div>
          <div className="mb-1 flex items-center gap-2"><span className="text-white/80 text-xs">◈</span><span className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/80">Compliance Engine</span></div>
          <h1 className="text-3xl font-bold text-white mb-3">
            {isCandidate ? 'Audit Your Resume' : 'Resume Bias Audit'}
          </h1>
          <p className="text-white/90 text-sm max-w-xl leading-relaxed mb-8">
            {isCandidate
              ? 'Upload your resume to see how it scores against your target role and discover any bias signals that could affect your chances.'
              : 'Upload candidate profiles to scan for unconscious bias indicators in formatting, language, and institutional markers. Engineered for objective evaluation.'
            }
          </p>
          <div className="mb-6 max-w-xl">
            <label className="block text-xs font-bold uppercase tracking-widest text-white mb-2 flex items-center gap-2">Target Role
              {s.detectingRole && <span className="flex items-center gap-1.5 text-white/90 font-normal normal-case tracking-normal"><RefreshCw className="w-3 h-3 animate-spin" />Detecting...</span>}
              {!s.detectingRole && s.jobRole && s.selectedFile && <span className="flex items-center gap-1 text-white font-normal normal-case tracking-normal"><Check className="w-3 h-3" />Detected</span>}
            </label>
            <input type="text" value={s.jobRole} onChange={e => s.setJobRole(e.target.value)} placeholder={s.detectingRole ? 'Detecting...' : 'e.g. Full Stack Engineer'} disabled={s.detectingRole}
              className="w-full glass-input rounded-xl px-4 py-3 text-sm text-white placeholder-white/20" />
          </div>

          {/* ── Inline file rejection / warning error banner ── */}
          {s.fileUploadError && (() => {
            const isWarning = s.fileUploadError.includes('AI service busy');
            const border = isWarning ? 'border-yellow-500/30' : 'border-red-500/30';
            const bg     = isWarning ? 'bg-yellow-500/[0.07]' : 'bg-red-500/[0.08]';
            const icon   = isWarning ? 'text-yellow-400' : 'text-red-400';
            const title  = isWarning ? 'text-yellow-300' : 'text-red-300';
            const body   = isWarning ? 'text-yellow-300/80' : 'text-red-300/80';
            return (
              <div className={`mb-5 max-w-xl flex items-start gap-3 px-4 py-3 rounded-xl border ${border} ${bg} animate-fade-in`}>
                <AlertTriangle className={`w-4 h-4 ${icon} shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-semibold ${title} mb-0.5`}>
                    {isWarning ? 'Detection Warning' : 'Invalid Document'}
                  </div>
                  <div className={`text-xs ${body} leading-relaxed`}>{s.fileUploadError}</div>
                  {!isWarning && (
                    <div className="text-xs text-white/40 mt-1">Please upload a valid resume or CV (PDF or image).</div>
                  )}
                </div>
                <button
                  onClick={() => s.setFileUploadError(null)}
                  className="text-white/30 hover:text-white/60 transition-colors shrink-0 mt-0.5"
                  aria-label="Dismiss"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            );
          })()}

          <input ref={s.fileInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.gif" style={{ display: 'none' }} onChange={e => s.handleFileSelect(e.target.files[0])} />
          {!s.selectedFile ? (
            <div onClick={() => s.fileInputRef.current.click()} onDragOver={e => { e.preventDefault(); s.setDragOver(true); }} onDragLeave={() => s.setDragOver(false)}
              onDrop={e => { e.preventDefault(); s.setDragOver(false); s.handleFileSelect(e.dataTransfer.files[0]); }}
              className={'relative rounded-2xl border border-dashed cursor-pointer transition-all duration-500 var(--bezier-smooth) flex flex-col items-center justify-center py-10 sm:py-20 group overflow-hidden ' + (s.dragOver ? 'border-white/40 bg-white/[0.04]' : 'border-white/10 bg-black hover:border-white/30 hover:bg-white/[0.02]')}
              style={{ boxShadow: s.dragOver ? 'inset 0 0 40px rgba(255,255,255,0.05)' : 'none' }}>
              <div className={'w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-all duration-500 border ' + (s.dragOver ? 'bg-white/10 border-white/20 scale-110 shadow-[0_0_20px_rgba(255,255,255,0.1)]' : 'bg-white/[0.02] border-white/[0.05] group-hover:border-white/20 group-hover:bg-white/[0.05] group-hover:scale-105')}>
                <UploadCloud className="w-8 h-8 text-white group-hover:text-white transition-colors duration-500" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 tracking-tight text-center">Drag & Drop Resumes</h3>
              <p className="text-white/90 text-sm mb-5 text-center max-w-sm px-4">
                Supported formats: PDF, DOCX, TXT. System automatically redacts Personally Identifiable Information (PII) prior to analysis.
              </p>
              <button className="px-6 py-2.5 rounded-xl text-xs font-bold tracking-widest uppercase btn-premium shrink-0">Select Files</button>
            </div>
          ) : (
            <div className="rounded-2xl border border-white/10 glass-card glass-card-hover p-4 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-5">
              <div className="flex items-center gap-4 w-full min-w-0">
                <div className="w-12 h-12 sm:w-14 sm:h-14 shrink-0 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center">
                  <FileText className="w-6 h-6 sm:w-7 sm:h-7 text-white/90" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-white mb-0.5 truncate">{s.selectedFile.name}</div>
                  <div className="text-xs text-white/80 truncate">{(s.selectedFile.size / 1024).toFixed(1)} KB · Ready</div>
                </div>
              </div>
              <div className="flex items-center gap-2 sm:gap-3 w-full sm:w-auto justify-end shrink-0 pt-2 sm:pt-0 border-t border-white/[0.05] sm:border-0">
                <button onClick={() => { s.setSelectedFile(null); if (s.fileInputRef.current) s.fileInputRef.current.value = ''; }} className="p-2 sm:p-2.5 text-white/80 hover:text-white hover:bg-white/[0.06] rounded-xl transition-colors bg-white/[0.02] border border-white/[0.05]">
                  <XCircle className="w-4 h-4 sm:w-5 sm:h-5" />
                </button>
                <button onClick={s.startScan} disabled={s.detectingRole || !s.jobRole}
                  className={'flex-1 sm:flex-none justify-center px-4 sm:px-6 py-2 sm:py-2.5 rounded-xl bg-white text-black font-bold text-sm hover:bg-white/90 transition-all active:scale-95 flex items-center gap-2 ' + (s.detectingRole || !s.jobRole ? 'opacity-40 cursor-not-allowed' : '')}>
                  <Zap className="w-4 h-4" />Analyze
                </button>
              </div>
            </div>
          )}
          <div className="mt-5 flex flex-wrap gap-3 items-center">
            <button onClick={s.loadDemo} className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white text-xs font-semibold hover:bg-white/[0.08] transition-colors ml-auto">
              <Play className="w-3.5 h-3.5" />Try Sample Demo
            </button>
          </div>
          <ArchitectureDiagram />
          {/* JD Bias Analyzer is a recruiter-only tool */}
          {!isCandidate && (
            <JDAnalysisSection jdText={s.jdText} setJdText={s.setJdText} jdResult={s.jdResult} analyzing={s.jdAnalyzing} onAnalyze={s.handleJDAnalysis} expanded={s.jdExpanded} setExpanded={s.setJdExpanded} isDemo={s.isDemo} demoResult={DEMO_JD_RESULT} />
          )}
        </div>
        <div className="space-y-4">
          <div className="glass-card glass-card-hover rounded-2xl p-5 hover-glow scroll-animate">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-white">Audit Engine Status</div>
              <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />ONLINE
              </span>
            </div>
            <div className="text-xs text-white/40">Compliance pipeline ready. Upload a resume to begin analysis.</div>
          </div>
          <div className="glass-card glass-card-hover rounded-2xl p-5 hover-glow scroll-animate">
            <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-white mb-4">Recent Scans</div>
            {scansLoading && (
              <div className="flex items-center gap-2 text-xs text-white/30 py-4">
                <span className="w-3.5 h-3.5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
                Loading…
              </div>
            )}
            {!scansLoading && recentScans.length === 0 && (
              <div className="text-xs text-white/25 py-3 text-center">No scans yet — upload your first resume!</div>
            )}
            {!scansLoading && recentScans.map((scan, i) => (
              <div key={scan.id} className="flex items-center gap-3 py-3 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] -mx-2 px-2 rounded-lg transition-colors cursor-pointer group">
                <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-xs text-white/80">
                  <FileText className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{scan.file_name || scan.role_target}</div>
                  <div className="text-xs text-white/40 flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5" />{fmtTime(scan.timestamp)}
                    <span className="mx-1">·</span>
                    <span className={`font-bold ${ scan.fit_score >= 70 ? 'text-emerald-400' : scan.fit_score >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>{scan.fit_score}</span>
                  </div>
                </div>
                <span className="text-white/20 group-hover:text-white/50 transition-colors">→</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-6 glass-card glass-card-hover rounded-2xl p-5 scroll-animate">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-white">Audit Parameters</div>
          <button className="text-xs text-white/80 flex items-center gap-1 hover:text-white transition-colors">⚙ Advanced</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover-border-brighten">
            <div><div className="text-sm font-semibold text-white">PII Redaction</div><div className="text-xs text-white/80 mt-0.5">Remove names, addresses, emails</div></div>
            <ToggleSwitch active={s.piiRedaction} onToggle={() => s.setPiiRedaction(v => !v)} />
          </div>
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover-border-brighten">
            <div><div className="text-sm font-semibold text-white">Institution Masking</div><div className="text-xs text-white/80 mt-0.5">Obscure university/company names</div></div>
            <ToggleSwitch active={s.instMasking} onToggle={() => s.setInstMasking(v => !v)} />
          </div>
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover-border-brighten">
            <div><div className="text-sm font-semibold text-white">Gendered Language</div><div className="text-xs text-white/80 mt-0.5">Flag potentially biased semantics</div></div>
            <ToggleSwitch active={s.genderedLang} onToggle={() => s.setGenderedLang(v => !v)} />
          </div>
        </div>
      </div>
    </div>
  );
}
