export type ModelCard = {
  id: string;
  label: string;
  provider: string;
  family: string;
  transport: string;
  value: string;
  recommended_for: string[];
};

export type DatasetSpec = {
  id: string;
  purpose: string;
  source: string;
  format_hint: string;
  recommended_for: string[];
};

export type ProviderHealth = {
  provider: string;
  ok: boolean;
  detail: string;
};

export type TraceEvent = {
  kind: string;
  message: string;
  data: Record<string, unknown>;
};

export type ChatResponse = {
  answer: string;
  model_id: string;
  provider: string;
  plan_kind: string;
  confidence: number;
  traces: TraceEvent[];
};

export type TrainingStatus = {
  running: boolean;
  idle_seconds: number;
  last_dataset?: string | null;
  last_result?: string | null;
};

export type TrainingPlan = {
  backend: string;
  dataset_id: string;
  normalized_rows: number;
  command_hint: string;
  export_targets: string[];
  notes: string[];
};
