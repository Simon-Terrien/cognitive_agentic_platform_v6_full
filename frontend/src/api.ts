import { ChatResponse, DatasetSpec, ModelCard, ProviderHealth, TrainingPlan, TrainingStatus } from './types';

function resolveApiBase(): string {
  const configured = String(import.meta.env.VITE_API_BASE ?? '').trim();
  if (configured) {
    return `${configured.replace(/\/+$/, '')}/api`;
  }
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:15001/api`;
  }
  return 'http://localhost:15001/api';
}

const API_BASE = resolveApiBase();

async function readErrorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const payload = await res.json();
    if (typeof payload?.detail === 'string' && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
  }
  return fallback;
}

export async function fetchModels(): Promise<ModelCard[]> {
  const res = await fetch(`${API_BASE}/models`);
  return await res.json();
}

export async function fetchModel(modelId: string): Promise<ModelCard> {
  const res = await fetch(`${API_BASE}/models/${encodeURIComponent(modelId)}`);
  if (!res.ok) throw new Error(`Model lookup failed with ${res.status}`);
  return await res.json();
}

export async function fetchProviderStatus(): Promise<ProviderHealth[]> {
  const res = await fetch(`${API_BASE}/providers/status`);
  return await res.json();
}

export async function sendChat(message: string, modelId: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ message, model_id: modelId }),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res, `Chat failed with ${res.status}`));
  return await res.json();
}

export async function fetchTrainingStatus(): Promise<TrainingStatus> {
  const res = await fetch(`${API_BASE}/training/status`);
  return await res.json();
}

export async function fetchTrainingDatasets(): Promise<DatasetSpec[]> {
  const res = await fetch(`${API_BASE}/training/datasets`);
  return await res.json();
}

export async function startTraining(): Promise<TrainingStatus> {
  const res = await fetch(`${API_BASE}/training/start`, { method: 'POST' });
  return await res.json();
}

export async function stopTraining(): Promise<TrainingStatus> {
  const res = await fetch(`${API_BASE}/training/stop`, { method: 'POST' });
  return await res.json();
}

export async function fetchTrainingPlan(modelId: string, datasetId?: string): Promise<TrainingPlan> {
  const params = new URLSearchParams({ model_id: modelId });
  if (datasetId) params.set('dataset_id', datasetId);
  const res = await fetch(`${API_BASE}/training/plan?${params.toString()}`);
  return await res.json();
}

export function openChatStream(message: string, modelId: string): EventSource {
  const url = `${API_BASE}/chat/stream?message=${encodeURIComponent(message)}&model_id=${encodeURIComponent(modelId)}`;
  return new EventSource(url);
}
