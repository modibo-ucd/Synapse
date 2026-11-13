// API types mirroring the backend contract. snake_case is intentional;
// every additive (Phase A) field is optional.

export type StageName = 'plan' | 'retrieve' | 'tools' | 'review' | 'answer'

/** UI/timeline status. The completed `/ask` trace only emits done|skipped|error. */
export type StageStatus = 'pending' | 'running' | 'done' | 'skipped' | 'error'

export interface Citation {
  id: string
  source_file: string
  /** Always present in the backend response. */
  section: string
  chunk_id: string
  excerpt: string
}

export interface SubGoal {
  id: string
  question: string
  intent: string
  entities: string[]
}

export interface Plan {
  complexity: 'simple' | 'multi_hop'
  in_scope: boolean
  sub_goals: SubGoal[]
}

export type ReviewVerdict = 'pass' | 'revise' | 'insufficient_evidence'

export interface ReviewInfo {
  verdict: ReviewVerdict
  unsupported_claims: string[]
  ambiguity_flags: string[]
}

export type ToolCallStatus = 'ok' | 'error' | 'timeout'

export interface ToolCallInfo {
  tool: string
  arguments: Record<string, unknown>
  status: ToolCallStatus
}

export interface Usage {
  tokens_in: number
  tokens_out: number
}

export interface ComparisonCell {
  text: string
  citation_ids: string[]
}

export interface ComparisonRow {
  attribute: string
  values: Record<string, ComparisonCell>
}

export interface Comparison {
  drugs: string[]
  rows: ComparisonRow[]
}

export interface EgfrThreshold {
  value: number
  citation_ids: string[]
}

export interface EgfrWidget {
  type: 'egfr'
  thresholds: EgfrThreshold[]
}

export interface RetrievedChunk {
  chunk_id: string
  source_file: string
  section_path: string
  excerpt: string
  dense_rank: number | null
  bm25_rank: number | null
  fused_score: number
  cited: boolean
}

export interface RetrievalInfo {
  mode: 'hybrid' | 'bm25_only'
  candidates: number
  returned: number
  chunks: RetrievedChunk[]
}

export interface StageTrace {
  stage: StageName
  status: StageStatus
  duration_ms: number | null
  summary: string | null
}

export interface AskResponse {
  answer: string
  sources: string[]
  citations: Citation[]
  disclaimer: string
  plan?: Plan
  tool_calls: ToolCallInfo[]
  review: ReviewInfo
  retrieval_mode: 'hybrid' | 'bm25_only'
  retrieval?: RetrievalInfo | null
  trace?: StageTrace[] | null
  trace_id: string
  usage: Usage
  latency_ms: number
  comparison?: Comparison | null
  widgets?: EgfrWidget[] | null
}

export interface IndexStats {
  files: number
  chunks: number
  embedding_model: string | null
}

export interface HealthResponse {
  status: string
  index: 'building' | 'ready' | 'degraded'
  llm_configured: boolean
  version?: string
  index_stats?: IndexStats | null
}

export interface SourceChunkSpan {
  chunk_id: string
  section_path: string
  start: number
  end: number
}

export type SourceDocType = 'dailymed' | 'medlineplus' | 'glossary'

export interface SourceSummary {
  file_name: string
  title: string
  drug_name: string
  source_type: SourceDocType
  size_chars: number
}

export interface SourceDocument {
  file_name: string
  title: string
  drug_name: string
  source_type: SourceDocType
  markdown: string
  chunks: SourceChunkSpan[]
}

export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    request_id?: string | null
  }
}
