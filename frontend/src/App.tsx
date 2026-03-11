import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchModel, fetchModels, fetchProviderStatus, fetchTrainingDatasets, fetchTrainingPlan, fetchTrainingStatus, openChatStream, sendChat, startTraining, stopTraining } from './api';
import { ChatResponse, DatasetSpec, ModelCard, ProviderHealth, TraceEvent, TrainingPlan, TrainingStatus } from './types';

const defaultMessage = 'Explain when to use Ollama, vLLM, llama.cpp and Transformers in a local AI lab.';

export default function App() {
  const [models, setModels] = useState<ModelCard[]>([]);
  const [datasets, setDatasets] = useState<DatasetSpec[]>([]);
  const [providerStatus, setProviderStatus] = useState<ProviderHealth[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('ollama_qwen3');
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [message, setMessage] = useState(defaultMessage);
  const [answer, setAnswer] = useState<string>('');
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [streamed, setStreamed] = useState<string>('');
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);
  const [trainingPlan, setTrainingPlan] = useState<TrainingPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastError, setLastError] = useState<string | null>(null);
  const [activeGuideStep, setActiveGuideStep] = useState<string>('01');
  const [focusArea, setFocusArea] = useState<string | null>('telemetry');
  const [demoRunning, setDemoRunning] = useState(false);
  const [guideStatus, setGuideStatus] = useState('Ready to run the guided tour.');
  const modelsRef = useRef<ModelCard[]>([]);
  const datasetsRef = useRef<DatasetSpec[]>([]);

  useEffect(() => { refresh(); }, []);

  function getEffectiveModelId() {
    const availableModels = modelsRef.current;
    if (availableModels.some((model) => model.id === selectedModel)) {
      return selectedModel;
    }
    return availableModels[0]?.id ?? selectedModel;
  }

  function getEffectiveDatasetId() {
    const availableDatasets = datasetsRef.current;
    if (availableDatasets.some((dataset) => dataset.id === selectedDataset)) {
      return selectedDataset;
    }
    return availableDatasets[0]?.id ?? selectedDataset;
  }

  async function refresh() {
    setLoading(true);
    try {
      const [m, d, p, t] = await Promise.all([fetchModels(), fetchTrainingDatasets(), fetchProviderStatus(), fetchTrainingStatus()]);
      modelsRef.current = m;
      datasetsRef.current = d;
      setModels(m);
      setDatasets(d);
      setProviderStatus(p);
      setTrainingStatus(t);
      setLastError(null);
      if (!m.some((model) => model.id === selectedModel) && m.length > 0) {
        setSelectedModel(m[0].id);
      }
      if (!d.some((dataset) => dataset.id === selectedDataset) && d.length > 0) {
        setSelectedDataset(d[0].id);
      }
    } catch (err) {
      setLastError(err instanceof Error ? err.message : String(err));
      modelsRef.current = [];
      datasetsRef.current = [];
      setProviderStatus([]);
      setModels([]);
      setDatasets([]);
      setTrainingStatus(null);
    }
    finally {
      setLoading(false);
    }
  }

  async function handleAsk() {
    if (modelsRef.current.length === 0) return;
    const modelId = getEffectiveModelId();
    setBusy(true);
    setStreamed('');
    try {
      const payload: ChatResponse = await sendChat(message, modelId);
      setSelectedModel(modelId);
      setAnswer(payload.answer);
      setTraces(payload.traces);
      setLastError(null);
    } catch (err) {
      const text = err instanceof Error ? err.message : String(err);
      setLastError(text);
      setAnswer(text);
      setTraces([]);
    } finally {
      setBusy(false);
    }
  }

  function handleStream() {
    if (modelsRef.current.length === 0) return;
    const modelId = getEffectiveModelId();
    setBusy(true);
    setAnswer('');
    setTraces([]);
    setStreamed('');
    setSelectedModel(modelId);
    const es = openChatStream(message, modelId);
    es.onmessage = (event) => {
      const parsed: TraceEvent = JSON.parse(event.data);
      if (parsed.kind === 'token') {
        const token = String(parsed.data?.token ?? '');
        setStreamed((prev) => prev + token);
      } else if (parsed.kind === 'error') {
        setLastError(String(parsed.data?.detail ?? 'Streaming failed. Verify the backend API and provider path.'));
        es.close();
        setBusy(false);
      } else {
        setTraces((prev) => [...prev, parsed]);
        if (parsed.kind === 'final') {
          setAnswer(String(parsed.data?.answer ?? ''));
          setLastError(null);
          es.close();
          setBusy(false);
        }
      }
    };
    es.onerror = () => {
      setLastError('Streaming failed. Verify the backend API and provider path.');
      es.close();
      setBusy(false);
    };
  }

  async function handleTrainingPlan() {
    if (modelsRef.current.length === 0) return;
    const modelId = getEffectiveModelId();
    const datasetId = getEffectiveDatasetId();
    try {
      setSelectedModel(modelId);
      setSelectedDataset(datasetId);
      setTrainingPlan(await fetchTrainingPlan(modelId, datasetId || undefined));
      setLastError(null);
    } catch (err) {
      setLastError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleTrainingStart() {
    try {
      setTrainingStatus(await startTraining());
      setLastError(null);
    } catch (err) {
      setLastError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleTrainingStop() {
    try {
      setTrainingStatus(await stopTraining());
      setLastError(null);
    } catch (err) {
      setLastError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleReloadModel() {
    if (modelsRef.current.length === 0) return;
    const modelId = getEffectiveModelId();
    const model = await fetchModel(modelId);
    setSelectedModel(model.id);
    setModels((current) => current.map((item) => item.id === model.id ? model : item));
    modelsRef.current = modelsRef.current.map((item) => item.id === model.id ? model : item);
  }

  const activeModel = useMemo(() => models.find((m) => m.id === selectedModel) ?? null, [models, selectedModel]);
  const activeDataset = useMemo(() => datasets.find((dataset) => dataset.id === selectedDataset) ?? null, [datasets, selectedDataset]);
  const healthyProviders = providerStatus.filter((item) => item.ok).length;
  const telemetryMode = loading ? 'syncing' : lastError ? 'degraded' : 'online';
  const canRunMission = !busy && models.length > 0;
  const providerCards = providerStatus.length > 0
    ? providerStatus
    : [{
        provider: loading ? 'Telemetry sync' : 'Backend offline',
        ok: loading,
        detail: loading ? 'Fetching control-plane health' : 'Start the API or set VITE_API_BASE to restore live telemetry.',
      }];
  const traceKinds = useMemo(() => {
    const counts = new Map<string, number>();
    for (const trace of traces) {
      counts.set(trace.kind, (counts.get(trace.kind) ?? 0) + 1);
    }
    return Array.from(counts.entries());
  }, [traces]);
  const answerText = answer || streamed || (loading ? 'Waiting for telemetry sync.' : lastError ? 'Control plane degraded. Restore backend connectivity to resume live orchestration.' : 'No answer yet.');
  const missionSignals = [
    { label: 'Selected model', value: activeModel?.label ?? (loading ? 'syncing' : 'awaiting backend'), accent: 'cyan' },
    { label: 'Dataset mode', value: activeDataset?.id ?? (loading ? 'loading' : 'none selected'), accent: 'emerald' },
    { label: 'Output state', value: streamed ? 'live response' : answer ? 'brief ready' : loading ? 'warming up' : 'awaiting run', accent: 'amber' },
    { label: 'Control room', value: busy ? 'active cycle' : telemetryMode, accent: busy ? 'emerald' : lastError ? 'amber' : 'slate' },
  ];
  const topologyNodes = [
    { label: 'Prompt ingress', value: `${message.trim().length} chars`, accent: 'cyan' },
    { label: activeModel?.provider ?? 'Model router', value: activeModel?.label ?? (loading ? 'syncing' : 'waiting for model'), accent: 'emerald' },
    { label: 'Trace bus', value: traces.length > 0 ? `${traces.length} frames` : 'idle', accent: 'amber' },
    { label: 'Training loop', value: trainingStatus?.running ? 'scheduler active' : loading ? 'syncing' : 'scheduler idle', accent: trainingStatus?.running ? 'emerald' : 'slate' },
  ];
  const workflowSteps = [
    { label: 'Models online', value: loading ? 'syncing' : providerStatus.length > 0 ? `${healthyProviders}/${providerStatus.length}` : 'offline', accent: 'cyan' },
    { label: 'Trace frames', value: `${traces.length}`, accent: 'amber' },
    { label: 'Datasets loaded', value: loading ? 'syncing' : lastError && datasets.length === 0 ? 'offline' : `${datasets.length}`, accent: 'emerald' },
    { label: 'Scheduler', value: trainingStatus?.running ? 'active' : loading ? 'syncing' : lastError ? 'degraded' : 'idle', accent: trainingStatus?.running ? 'emerald' : 'slate' },
  ];
  const operatingLanes = [
    { lane: 'Demo', mission: 'Show the control plane in under five minutes.', command: 'Refresh telemetry, keep a local model selected, then Run mission.', success: `${healthyProviders}/${providerCards.length} providers visible and answer panel populated.` },
    { lane: 'Testing', mission: 'Validate request, stream, and training paths before a change lands.', command: 'Run once, stream reasoning, then build a training plan.', success: 'Trace frames appear, SSE completes, and plan output shows backend plus export targets.' },
    { lane: 'Dev', mission: 'Inspect model routing and local iteration details while modifying the stack.', command: 'Switch models, reload model metadata, and inspect trace JSON after each run.', success: `${activeModel?.provider ?? 'model router'} stays selected and traces reflect the selected runtime.` },
    { lane: 'Observability', mission: 'Use the dashboard as a live health board for providers and scheduler state.', command: 'Watch Provider Matrix, Mission Flow, and scheduler cards while services change.', success: `${telemetryMode} telemetry with provider detail strings and scheduler status updates.` },
  ];
  const backendSurface = [
    { surface: '/api/health', purpose: 'Backend heartbeat and frontend boot check.', status: '200 with ok=true', use: 'Confirms the API is reachable before any chat or training request.' },
    { surface: '/api/models', purpose: 'Load model catalog for routing and selector population.', status: `${models.length || 0} models loaded`, use: 'Drives model selection, labels, and provider transport display.' },
    { surface: '/api/providers/status', purpose: 'Provider readiness for Ollama, vLLM, llama.cpp, and others.', status: `${healthyProviders}/${providerCards.length} healthy`, use: 'Feeds the ribbon, topology list, and system pulse cards.' },
    { surface: '/api/training/status', purpose: 'Training scheduler proxy state.', status: trainingStatus?.running ? 'scheduler active' : 'scheduler idle', use: 'Backs the scheduler controls and training telemetry.' },
    { surface: '/api/chat + /api/chat/stream', purpose: 'One-shot and SSE mission execution.', status: traces.length > 0 ? `${traces.length} trace frames` : 'idle', use: 'Powers answer synthesis, trace timeline, and streamed response view.' },
  ];
  const tutorialSteps = [
    { step: '01', title: 'Synchronize telemetry', body: 'Use Refresh telemetry or Sync control room to load the live backend state before demoing anything.', hint: 'You should see provider chips, dataset counts, and scheduler state settle.' },
    { step: '02', title: 'Choose the runtime path', body: 'Select a model in Model Control and optionally choose a training dataset to frame the mission.', hint: `Current default path: ${activeModel?.label ?? 'awaiting model catalog'}.` },
    { step: '03', title: 'Run or stream a mission', body: 'Use Run once for a stable answer or Stream reasoning to show progressive SSE frames in the trace timeline.', hint: 'The answer panel should update while trace cards accumulate in the center column.' },
    { step: '04', title: 'Inspect training and observability', body: 'Build a training plan, then read Provider Matrix and Mission Flow to explain what the backend is doing.', hint: 'This is the fastest way to show demo, testing, development, and observability workflows in one view.' },
  ];
  const highlightedArea = focusArea ?? 'telemetry';

  function panelClass(base: string, area: string) {
    return `${base} ${highlightedArea === area ? 'panel-focus' : 'panel-muted'}`;
  }

  async function runGuideStep(step: string) {
    setActiveGuideStep(step);
    if (step === '01') {
      setFocusArea('telemetry');
      setGuideStatus('Synchronizing telemetry and provider health.');
      await refresh();
      return;
    }
    if (step === '02') {
      setFocusArea('model');
      setGuideStatus(`Reviewing the active runtime path: ${activeModel?.label ?? getEffectiveModelId()}.`);
      return;
    }
    if (step === '03') {
      setFocusArea('mission');
      setGuideStatus('Running a guided mission through the backend chat pipeline.');
      await handleAsk();
      return;
    }
    setFocusArea('operations');
    setGuideStatus('Building the training and observability readout.');
    await handleTrainingPlan();
  }

  async function runGuidedSequence() {
    if (demoRunning) return;
    setDemoRunning(true);
    setGuideStatus('Launching guided showcase.');
    try {
      await runGuideStep('01');
      await new Promise((resolve) => window.setTimeout(resolve, 220));
      await runGuideStep('02');
      await new Promise((resolve) => window.setTimeout(resolve, 220));
      await runGuideStep('03');
      await new Promise((resolve) => window.setTimeout(resolve, 220));
      await runGuideStep('04');
      setGuideStatus('Guided tour complete. The dashboard is primed for a live walkthrough.');
    } finally {
      setDemoRunning(false);
    }
  }

  return (
    <div className={`app-shell app-shell-${highlightedArea}`}>
      <div className="ambient-grid" aria-hidden="true" />
      <div className="ambient-orb ambient-orb-a" aria-hidden="true" />
      <div className="ambient-orb ambient-orb-b" aria-hidden="true" />
      <div className="ambient-orb ambient-orb-c" aria-hidden="true" />
      <div className="ambient-beacon" aria-hidden="true" />

      <header className={panelClass('hero-panel panel', 'telemetry')}>
        <div className="eyebrow">R&D Command Surface</div>
        <div className="hero-copy">
          <div>
            <h1>Cognitive Agentic Platform</h1>
            <p>
              A local AI research front-end designed to make model orchestration, provider health, trace visibility,
              and training strategy look investment-ready while staying operational.
            </p>
            <div className={`telemetry-banner telemetry-${telemetryMode}`}>
              <span className="telemetry-dot" />
              <strong>{loading ? 'Synchronizing telemetry' : lastError ? 'Telemetry degraded' : 'Telemetry online'}</strong>
              <span className="provider-detail">
                {loading ? 'Connecting to the backend control plane.' : lastError ?? 'Live provider, dataset, and scheduler telemetry available.'}
              </span>
            </div>
          </div>
          <div className="hero-actions">
            <button className="btn" onClick={handleAsk} disabled={!canRunMission}>Run mission</button>
            <button className="btn btn-ghost" onClick={handleStream} disabled={!canRunMission}>Stream live reasoning</button>
            <button className="btn btn-ghost" onClick={refresh}>Refresh telemetry</button>
          </div>
        </div>

        <div className="hero-metrics">
          {workflowSteps.map((step, index) => (
            <div className={`metric-card accent-${step.accent}`} key={step.label} style={{ animationDelay: `${index * 90}ms` }}>
              <div className="metric-label">{step.label}</div>
              <div className="metric-value">{step.value}</div>
            </div>
          ))}
        </div>

        <div className="provider-ribbon">
          {providerCards.map((item) => (
            <div className={`provider-chip ${item.ok ? 'provider-chip-ok' : 'provider-chip-bad'}`} key={item.provider}>
              <span className={`status-dot ${item.ok ? 'status-ok' : 'status-bad'}`} />
              <span>{item.provider}</span>
              <span className="provider-detail">{item.detail}</span>
            </div>
          ))}
        </div>

        <div className="mission-strip">
          {missionSignals.map((signal) => (
            <div className={`mission-card accent-${signal.accent}`} key={signal.label}>
              <div className="mission-label">{signal.label}</div>
              <div className="mission-value">{signal.value}</div>
            </div>
          ))}
        </div>
      </header>

      <div className="main-layout">
        <aside className="column column-left">
          <section className={panelClass('panel stack-panel', 'model')}>
            <div className="section-kicker">Inference Deck</div>
            <h2>Model Control</h2>
            <label className="label">Active model</label>
            <select className="select" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              {models.length === 0 && <option value={selectedModel}>{loading ? 'Loading models...' : 'Backend offline'}</option>}
              {models.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
            <div className="button-row">
              <button className="btn btn-ghost" onClick={handleReloadModel} disabled={models.length === 0}>Reload model</button>
              <button className="btn btn-ghost" onClick={refresh}>Sync control room</button>
            </div>
            {activeModel && (
              <div className="dossier-card">
                <div className="dossier-header">
                  <div>
                    <div className="dossier-title">{activeModel.label}</div>
                    <div className="dossier-meta">{activeModel.provider} · {activeModel.family} · {activeModel.transport}</div>
                  </div>
                  <div className="signal-pill">ready</div>
                </div>
                <div className="dossier-grid">
                  <div className="dossier-item">
                    <span className="muted">Runtime value</span>
                    <strong>{activeModel.value}</strong>
                  </div>
                  <div className="dossier-item">
                    <span className="muted">Recommended use</span>
                    <strong>{activeModel.recommended_for[0] ?? 'general'}</strong>
                  </div>
                </div>
                <div className="tag-row">
                  {activeModel.recommended_for.map((entry) => <span className="soft-tag" key={entry}>{entry}</span>)}
                </div>
              </div>
            )}
          </section>

          <section className={panelClass('panel stack-panel', 'operations')}>
            <div className="section-kicker">Training Loop</div>
            <h2>Dataset & Scheduler</h2>
            <label className="label">Training dataset</label>
            <select className="select" value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
              {datasets.length === 0 && <option value={selectedDataset}>{loading ? 'Loading datasets...' : 'No dataset telemetry'}</option>}
              {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.id}</option>)}
            </select>
            {activeDataset && (
              <div className="dataset-card">
                <div className="dataset-title">{activeDataset.purpose}</div>
                <div className="dataset-meta">{activeDataset.source} · {activeDataset.format_hint}</div>
              </div>
            )}
            <div className="kv-grid">
              <div className="kv-cell"><span className="muted">Scheduler</span><strong>{trainingStatus?.running ? 'active' : 'idle'}</strong></div>
              <div className="kv-cell"><span className="muted">Idle seconds</span><strong>{trainingStatus?.idle_seconds ?? '-'}</strong></div>
              <div className="kv-cell"><span className="muted">Last dataset</span><strong>{trainingStatus?.last_dataset ?? '-'}</strong></div>
              <div className="kv-cell"><span className="muted">Dataset count</span><strong>{datasets.length}</strong></div>
            </div>
            <div className="button-row">
              <button className="btn" onClick={handleTrainingStart} disabled={!!lastError}>Start scheduler</button>
              <button className="btn btn-ghost" onClick={handleTrainingStop} disabled={!!lastError}>Stop scheduler</button>
              <button className="btn btn-ghost" onClick={handleTrainingPlan} disabled={models.length === 0}>Build plan</button>
            </div>
          </section>
        </aside>

        <main className="column column-center">
          <section className={panelClass('panel narrative-panel', 'mission')}>
            <div className="section-kicker">Mission Prompt</div>
            <div className="narrative-header">
              <div>
                <h2>Reasoning Workspace</h2>
                <p className="muted">
                  Frame the R&amp;D objective, run a one-shot answer, or stream reasoning to show the system thinking in public.
                </p>
              </div>
              <div className="signal-cluster">
                <span className={`signal-pill ${busy ? 'signal-live' : ''}`}>{busy ? 'streaming' : 'standby'}</span>
                <span className="signal-pill">{activeModel?.label ?? selectedModel}</span>
              </div>
            </div>
            <textarea className="textarea textarea-primary" value={message} onChange={(e) => setMessage(e.target.value)} />
            <div className="button-row">
              <button className="btn" onClick={handleAsk} disabled={!canRunMission}>Run once</button>
              <button className="btn btn-ghost" onClick={handleStream} disabled={!canRunMission}>Stream reasoning</button>
            </div>
          </section>

          <section className={panelClass('panel answer-panel', 'mission')}>
            <div className="section-kicker">Synthesis</div>
            <div className="answer-header">
              <h2>Executive Answer</h2>
              <div className="answer-badge">{streamed ? 'live stream' : 'final brief'}</div>
            </div>
            <div className="answer-copy">{answerText}</div>
          </section>

          <section className={panelClass('panel trace-panel', 'mission')}>
            <div className="trace-header">
              <div>
                <div className="section-kicker">Reasoning Telemetry</div>
                <h2>Trace Timeline</h2>
              </div>
              <div className="trace-summary">
                {traceKinds.length === 0 ? <span className="soft-tag">no frames yet</span> : traceKinds.map(([kind, count]) => <span className="soft-tag" key={kind}>{kind} · {count}</span>)}
              </div>
            </div>
            <div className="trace-stream">
              {traces.length === 0 ? (
                <div className="trace-empty">Start a run to render the reasoning path, tool outputs, and final synthesis frames.</div>
              ) : traces.map((trace, index) => (
                <article className="trace-card" key={`${trace.kind}-${index}`}>
                  <div className="trace-rail" />
                  <div className="trace-card-head">
                    <span className="trace-kind">{trace.kind}</span>
                    <strong>{trace.message}</strong>
                  </div>
                  <div className="code-block">{JSON.stringify(trace.data, null, 2)}</div>
                </article>
              ))}
            </div>
          </section>

          <section className={panelClass('panel stack-panel', 'telemetry')}>
            <div className="section-kicker">Operating Lanes</div>
            <h2>Demo, Testing, Dev, Observability</h2>
            <div className="table-shell">
              <table className="matrix-table">
                <thead>
                  <tr>
                    <th>Lane</th>
                    <th>Mission</th>
                    <th>What to do</th>
                    <th>Success signal</th>
                  </tr>
                </thead>
                <tbody>
                  {operatingLanes.map((lane) => (
                    <tr key={lane.lane}>
                      <td data-label="Lane"><span className="table-chip">{lane.lane}</span></td>
                      <td data-label="Mission">{lane.mission}</td>
                      <td data-label="What to do">{lane.command}</td>
                      <td data-label="Success signal">{lane.success}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={panelClass('panel stack-panel', 'telemetry')}>
            <div className="section-kicker">Backend Surface</div>
            <h2>What The Frontend Uses</h2>
            <div className="table-shell">
              <table className="matrix-table matrix-table-compact">
                <thead>
                  <tr>
                    <th>Endpoint</th>
                    <th>Purpose</th>
                    <th>Live state</th>
                    <th>Usage</th>
                  </tr>
                </thead>
                <tbody>
                  {backendSurface.map((item) => (
                    <tr key={item.surface}>
                      <td data-label="Endpoint"><span className="table-code">{item.surface}</span></td>
                      <td data-label="Purpose">{item.purpose}</td>
                      <td data-label="Live state">{item.status}</td>
                      <td data-label="Usage">{item.use}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={panelClass('panel stack-panel', 'mission')}>
            <div className="section-kicker">Usage Tutorial</div>
            <div className="tutorial-header">
              <div>
                <h2>Operator Runbook</h2>
                <div className="tutorial-status">{guideStatus}</div>
              </div>
              <div className="tutorial-actions">
                <button className="btn" onClick={runGuidedSequence} disabled={demoRunning || busy}>
                  {demoRunning ? 'Running guided sequence' : 'Launch wow sequence'}
                </button>
                <button className="btn btn-ghost" onClick={() => handleStream()} disabled={!canRunMission}>
                  Stream live moment
                </button>
              </div>
            </div>
            <div className="tutorial-grid">
              {tutorialSteps.map((item) => (
                <article className={`tutorial-card ${activeGuideStep === item.step ? 'tutorial-card-active' : ''}`} key={item.step}>
                  <div className="tutorial-step">{item.step}</div>
                  <div className="tutorial-title">{item.title}</div>
                  <p>{item.body}</p>
                  <div className="tutorial-hint">{item.hint}</div>
                  <div className="tutorial-card-actions">
                    <button className="btn" onClick={() => runGuideStep(item.step)} disabled={busy}>
                      {item.step === '01' ? 'Sync now' : item.step === '02' ? 'Focus model lane' : item.step === '03' ? 'Run mission now' : 'Build observability readout'}
                    </button>
                    {item.step === '03' && (
                      <button className="btn btn-ghost" onClick={() => { setActiveGuideStep(item.step); setFocusArea('mission'); setGuideStatus('Streaming the mission live through SSE.'); handleStream(); }} disabled={!canRunMission}>
                        Stream it
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </main>

        <aside className="column column-right">
          <section className={panelClass('panel stack-panel topology-panel', 'telemetry')}>
            <div className="section-kicker">Live Topology</div>
            <h2>Mission Flow</h2>
            <div className="topology-grid">
              {topologyNodes.map((node) => (
                <div className={`topology-node accent-${node.accent}`} key={node.label}>
                  <div className="topology-node-label">{node.label}</div>
                  <strong>{node.value}</strong>
                </div>
              ))}
            </div>
            <div className="topology-links" aria-hidden="true">
              <span className="topology-link topology-link-a" />
              <span className="topology-link topology-link-b" />
              <span className="topology-link topology-link-c" />
            </div>
            <div className="topology-provider-list">
              {providerCards.map((item) => (
                <div className="topology-provider" key={item.provider}>
                  <span className={`status-dot ${item.ok ? 'status-ok' : 'status-bad'}`} />
                  <span>{item.provider}</span>
                  <span className="provider-detail">{item.ok ? 'ready path' : 'manual check'}</span>
                </div>
              ))}
            </div>
          </section>

          <section className={panelClass('panel stack-panel', 'operations')}>
            <div className="section-kicker">System Pulse</div>
            <h2>Provider Matrix</h2>
            <div className="status-stack">
              {providerCards.map((item) => (
                <div key={item.provider} className="status-card">
                  <div className="status-card-head">
                    <strong>{item.provider}</strong>
                    <span className={`signal-pill ${item.ok ? 'signal-ok' : 'signal-danger'}`}>{item.ok ? 'online' : 'offline'}</span>
                  </div>
                  <div className="status-detail">{item.detail}</div>
                </div>
              ))}
            </div>
          </section>

          <section className={panelClass('panel stack-panel', 'operations')}>
            <div className="section-kicker">Training Readout</div>
            <h2>Plan Output</h2>
            {trainingPlan ? (
              <>
                <div className="kv-grid">
                  <div className="kv-cell"><span className="muted">Backend</span><strong>{trainingPlan.backend}</strong></div>
                  <div className="kv-cell"><span className="muted">Dataset</span><strong>{trainingPlan.dataset_id}</strong></div>
                  <div className="kv-cell"><span className="muted">Rows</span><strong>{trainingPlan.normalized_rows}</strong></div>
                  <div className="kv-cell"><span className="muted">Targets</span><strong>{trainingPlan.export_targets.length}</strong></div>
                </div>
                <div className="code-block code-block-tight">{trainingPlan.command_hint}</div>
                <div className="tag-row">
                  {trainingPlan.export_targets.map((target) => <span className="soft-tag" key={target}>{target}</span>)}
                </div>
                <div className="status-stack compact">
                  {trainingPlan.notes.map((note, idx) => <div className="status-card" key={idx}><div className="status-detail">{note}</div></div>)}
                </div>
              </>
            ) : (
              <div className="trace-empty">Build a plan to expose the dataset normalization workflow, backend choice, and deployment targets.</div>
            )}
          </section>

          <section className={panelClass('panel stack-panel', 'telemetry')}>
            <div className="section-kicker">Funding Narrative</div>
            <h2>What This Demonstrates</h2>
            <div className="narrative-list">
              <div className="narrative-item"><span>01</span><p>Unified local model orchestration without rewriting the agent runtime.</p></div>
              <div className="narrative-item"><span>02</span><p>Transparent reasoning traces that make the platform legible to technical and executive stakeholders.</p></div>
              <div className="narrative-item"><span>03</span><p>Training-readiness with visible datasets, scheduling, and export targets for future fine-tuning programs.</p></div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
