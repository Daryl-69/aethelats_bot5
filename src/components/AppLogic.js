import { useState, useRef, useEffect } from 'react';
import { API_URL, SCAN_LOGS, DEMO_RESULT, DEMO_CF_RESULT, DEMO_MULTIMODEL, DEMO_JD_RESULT, DEMO_PROOF_RESULT, DEMO_COMPARISON } from './constants';
import { useAuth } from '../context/AuthContext';

export function useAppState() {
  const { authHeaders } = useAuth();
  const getHashStep = () => window.location.hash.replace('#', '') || 'landing';
  const [step, setStepInternal] = useState(getHashStep());

  const setStep = (newStep) => {
    if (newStep !== step) {
      window.history.pushState(null, '', `#${newStep}`);
      setStepInternal(newStep);
    }
  };

  useEffect(() => {
    const handlePopState = () => {
      setStepInternal(getHashStep());
    };
    window.addEventListener('popstate', handlePopState);
    // Ensure initial load without hash sets it to landing in history if needed
    if (!window.location.hash) {
        window.history.replaceState(null, '', '#landing');
    }
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobRole, setJobRole] = useState('');
  const [detectingRole, setDetectingRole] = useState(false);
  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [fileUploadError, setFileUploadError] = useState(null);
  const [isDemo, setIsDemo] = useState(false);
  const [showFairnessGate, setShowFairnessGate] = useState(false);
  const [fairnessConfirmed, setFairnessConfirmed] = useState(false);
  const [pendingAction, setPendingAction] = useState('');
  const [cfResult, setCfResult] = useState(null);
  const [runningCF, setRunningCF] = useState(false);
  const [jdText, setJdText] = useState('');
  const [jdResult, setJdResult] = useState(null);
  const [jdAnalyzing, setJdAnalyzing] = useState(false);
  const [jdExpanded, setJdExpanded] = useState(false);
  const [mmResult, setMmResult] = useState(null);
  const [runningMM, setRunningMM] = useState(false);
  const [proofResult, setProofResult] = useState(null);
  const [proofLoading, setProofLoading] = useState(false);
  const [compResult, setCompResult] = useState(null);
  const [runningComp, setRunningComp] = useState(false);
  const [piiRedaction, setPiiRedaction] = useState(true);
  const [instMasking, setInstMasking] = useState(true);
  const [genderedLang, setGenderedLang] = useState(false);
  
  // Batch upload state (lifted from BatchUploadView to persist across navigation)
  const [batchJobs, setBatchJobs] = useState([]);
  const [batchId, setBatchId] = useState(null);
  const [batchWs, setBatchWs] = useState(null);
  
  const fileInputRef = useRef(null);
  const progressRef = useRef(0);
  const progTimerRef = useRef(null);
  const logTimerRef = useRef(null);

  function loadDemo() {
    setIsDemo(true); setJobRole('Full Stack Engineer');
    setResult(DEMO_RESULT); setCfResult(null); setRunningCF(false); setMmResult(null); setRunningMM(false);
    setFairnessConfirmed(false); setStep('results');
    setJdResult(null); setProofResult(null); setJdExpanded(false);
    setCompResult(null); setRunningComp(false);
  }
  function startScan() {
    if (!selectedFile) return;
    setStep('scanning'); setProgress(0); setLogs([]);
    setApiError(null); setFairnessConfirmed(false);
    setCfResult(null); progressRef.current = 0;
  }
  useEffect(() => {
    if (step !== 'scanning') return;
    let cancelled = false;
    setLogs([]); progressRef.current = 0;
    progTimerRef.current = setInterval(() => {
      if (cancelled) return;
      progressRef.current = Math.min(progressRef.current + (Math.random() * 1.8 + 0.4), 88);
      setProgress(Math.round(progressRef.current));
    }, 200);
    let logIdx = 0;
    logTimerRef.current = setInterval(() => {
      if (cancelled) return;
      if (logIdx < SCAN_LOGS.length) { const entry = SCAN_LOGS[logIdx]; if (entry) setLogs(prev => [...prev, entry]); logIdx++; }
    }, 650);
    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('role', jobRole || '');
    // Pass extracted skills from JD analyser so Bot 4 can score against the real JD
    if (jdResult?.required_skills?.length > 0) {
      fd.append('jd_skills', jdResult.required_skills.join(','));
    }
    fetch(API_URL + '/analyze', { method: 'POST', body: fd, headers: authHeaders() })
      .then(res => { if (!res.ok) return res.json().then(e => { throw new Error(e.detail || 'Failed'); }); return res.json(); })
      .then(data => {
        if (cancelled) return;
        
        const jobId = data.job_id;
        if (!jobId) {
            // Fallback if backend doesn't return job_id (e.g., using old backend temporarily)
            clearInterval(progTimerRef.current); clearInterval(logTimerRef.current);
            setProgress(100); setResult(data);
            setTimeout(() => setStep('results'), 600);
            return;
        }

        const pollInterval = setInterval(() => {
          fetch(API_URL + '/analyze/status/' + jobId, { headers: authHeaders() })
            .then(r => r.json())
            .then(statusData => {
              if (cancelled) { clearInterval(pollInterval); return; }
              if (statusData.status === 'completed') {
                clearInterval(pollInterval);
                clearInterval(progTimerRef.current); clearInterval(logTimerRef.current);
                setProgress(100); setResult(statusData.result);
                setTimeout(() => setStep('results'), 600);
              } else if (statusData.status === 'error') {
                clearInterval(pollInterval);
                clearInterval(progTimerRef.current); clearInterval(logTimerRef.current);
                setApiError(statusData.error || 'Failed during background processing'); setStep('error');
              }
            })
            .catch(err => console.error("Polling error:", err));
        }, 2000);
      })
      .catch(err => {
        if (cancelled) return;
        clearInterval(progTimerRef.current); clearInterval(logTimerRef.current);
        setApiError(err.message); setStep('error');
      });
    return () => { cancelled = true; clearInterval(progTimerRef.current); clearInterval(logTimerRef.current); };
  }, [step]);

  function reset() {
    setStep('upload'); setSelectedFile(null); setResult(null);
    setApiError(null); setFileUploadError(null); setProgress(0); setLogs([]);
    setJobRole(''); setDetectingRole(false); setIsDemo(false);
    setFairnessConfirmed(false); setShowFairnessGate(false);
    setCfResult(null); setRunningCF(false);
    setJdText(''); setJdResult(null); setJdAnalyzing(false); setJdExpanded(false);
    setProofResult(null); setProofLoading(false);
    setMmResult(null); setRunningMM(false);
    setCompResult(null); setRunningComp(false);
    
    // Clear batch state
    setBatchJobs([]);
    setBatchId(null);
    if (batchWs) {
      batchWs.close();
      setBatchWs(null);
    }
    
    progressRef.current = 0;
  }
  function handlePrimaryAction(label) {
    const proxies = result?.bias_proxies || [];
    if (proxies.length > 0 && !fairnessConfirmed) { setPendingAction(label); setShowFairnessGate(true); }
    else { console.log('[Aethel] Action confirmed:', label); }
  }
  function handleFairnessConfirm() {
    setShowFairnessGate(false); setFairnessConfirmed(true);
    alert('✅ Fairness review acknowledged.\n\nAction: ' + pendingAction);
  }
  function handleMultiModelTest() {
    if (isDemo) { setMmResult(DEMO_MULTIMODEL); return; }
    if (!selectedFile || !result) return;
    setRunningMM(true);
    const fd = new FormData(); fd.append('file', selectedFile); fd.append('role', jobRole || 'Software Engineer'); fd.append('baseline_score', String(result.fit_score || 70));
    fetch(API_URL + '/multi-model-test', { method: 'POST', body: fd })
      .then(res => res.ok ? res.json() : res.json().then(e => { throw new Error(e.detail); }))
      .then(data => { setMmResult(data); setRunningMM(false); })
      .catch(err => { console.error(err); setRunningMM(false); alert('Failed: ' + err.message); });
  }
  function handleCounterfactualTest() {
    if (isDemo) { setCfResult(DEMO_CF_RESULT); return; }
    if (!selectedFile || !result) return;
    setRunningCF(true);
    const fd = new FormData(); fd.append('file', selectedFile); fd.append('role', jobRole || 'Software Engineer'); fd.append('baseline_score', String(result.fit_score || 70));
    fetch(API_URL + '/counterfactual-test', { method: 'POST', body: fd })
      .then(res => res.ok ? res.json() : res.json().then(e => { throw new Error(e.detail); }))
      .then(data => { setCfResult(data); setRunningCF(false); })
      .catch(err => { console.error(err); setRunningCF(false); alert('Failed: ' + err.message); });
  }
  async function handleJDAnalysis(demoData) {
    if (demoData) { setJdResult(demoData); return; }
    if (!jdText.trim()) return;
    setJdAnalyzing(true);
    try {
      const resp = await fetch(API_URL + '/analyze-jd', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jd_text: jdText }) });
      const data = await (resp.ok ? resp.json() : resp.json().then(e => { throw new Error(e.detail); }));
      setJdResult(data);
      // Auto-update the target role from JD if a role was detected and user hasn't manually changed it
      if (data?.detected_role) {
        setJobRole(data.detected_role);
      }
    } catch (e) { alert('JD analysis failed: ' + e.message); } finally { setJdAnalyzing(false); }
  }
  async function handleProofOfWork() {
    if (isDemo) { setProofResult(DEMO_PROOF_RESULT); return; }
    const links = result?.detected_links || [];
    if (!links.length) return;
    setProofLoading(true);
    try {
      const resp = await fetch(API_URL + '/analyze-links', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ urls: links.map(l => l.url), role: jobRole || 'Software Engineer' }) });
      const data = await (resp.ok ? resp.json() : resp.json().then(e => { throw new Error(e.detail); }));
      setProofResult(data);
    } catch (e) { alert('Proof of work failed: ' + e.message); } finally { setProofLoading(false); }
  }

  async function handleModelComparison() {
    if (isDemo) { setCompResult(DEMO_COMPARISON); return; }
    if (!selectedFile || !result) return;
    setRunningComp(true);
    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('role', jobRole || 'Software Engineer');
    fd.append('baseline_score', String(result.fit_score || 70));
    // Pass signals/gaps from the already-computed Bot 4 result so the FairAI
    // row in the comparison panel shows real data without re-running any models
    fd.append('fairai_signals', JSON.stringify(result.strong_signals || []));
    fd.append('fairai_gaps',    JSON.stringify(result.gaps || []));
    fd.append('fairai_skills',  JSON.stringify(result.skill_matches || []));
    fd.append('fairai_recommendation', result.recommendation || 'Hire');
    fd.append('fairai_summary', result.summary || 'Bias-free evaluation via Bot 4.');
    try {
      const resp = await fetch(API_URL + '/compare-models', { method: 'POST', body: fd });
      const data = await (resp.ok ? resp.json() : resp.json().then(e => { throw new Error(e.detail); }));
      setCompResult(data);
    } catch (e) { console.error(e); alert('Model comparison failed: ' + e.message); }
    finally { setRunningComp(false); }
  }
  const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp', 'image/gif'];
  const ACCEPTED_EXTS = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.gif'];
  function handleFileSelect(f) {
    if (!f) return;
    const ok = ACCEPTED_TYPES.includes(f.type) || ACCEPTED_EXTS.some(e => f.name.toLowerCase().endsWith(e));
    if (!ok) { setFileUploadError('Please upload a PDF or image file (.pdf, .jpg, .png, .webp, .gif).'); return; }
    
    setFileUploadError(null);
    setSelectedFile(f); 
    setIsDemo(false);

    // If the JD analyzer or the user manually typed a role, DO NOT overwrite it.
    // Only detect the role if the box is currently completely empty.
    if (!jobRole || jobRole.trim() === '') {
      setDetectingRole(true);
      setFileUploadError(null);
      const fd = new FormData(); fd.append('file', f);
      fetch(API_URL + '/detect-role', { method: 'POST', body: fd })
        .then(async r => {
          if (!r.ok) {
            const errData = await r.json().catch(() => ({}));
            throw new Error(errData.detail || 'This file does not appear to be a valid resume or CV.');
          }
          return r.json();
        })
        .then(d => {
          setJobRole(d.role || '');
          if (!d.role && d.validation_warning) {
            // Backend accepted the file but couldn't run role detection (e.g. LLM rate-limited).
            // Show a soft warning — don't clear the file, let the user type the role manually.
            setFileUploadError(
              'Role auto-detection failed (AI service busy). You can type the role manually above to continue, or try uploading again.'
            );
          }
        })
        .catch(e => {
          // Stay on the upload page — show an inline error instead of the full error step
          setJobRole('');
          setSelectedFile(null);
          setFileUploadError(e.message);
          if (fileInputRef.current) fileInputRef.current.value = '';
        })
        .finally(() => setDetectingRole(false));
    }
  }

  return {
    step, setStep, progress, logs, dragOver, setDragOver, selectedFile, setSelectedFile, jobRole, setJobRole,
    detectingRole, result, setResult, apiError, fileUploadError, setFileUploadError, isDemo, showFairnessGate, setShowFairnessGate,
    fairnessConfirmed, cfResult, runningCF, jdText, setJdText, jdResult, jdAnalyzing,
    jdExpanded, setJdExpanded, mmResult, runningMM, proofResult, proofLoading,
    piiRedaction, setPiiRedaction, instMasking, setInstMasking, genderedLang, setGenderedLang,
    compResult, runningComp,
    batchJobs, setBatchJobs, batchId, setBatchId, batchWs, setBatchWs,
    fileInputRef, loadDemo, startScan, reset, handlePrimaryAction, handleFairnessConfirm,
    handleMultiModelTest, handleCounterfactualTest, handleJDAnalysis, handleProofOfWork,
    handleFileSelect, handleModelComparison, pendingAction,
  };
}
