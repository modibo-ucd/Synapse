import { z } from 'zod'

const STAGE_NAMES = ['plan', 'retrieve', 'tools', 'review', 'answer'] as const
const STAGE_STATUSES = ['pending', 'running', 'done', 'skipped', 'error'] as const

export const CitationSchema = z.object({
  id: z.string(),
  source_file: z.string(),
  section: z.string(),
  chunk_id: z.string(),
  excerpt: z.string(),
})

export const SubGoalSchema = z.object({
  id: z.string(),
  question: z.string(),
  intent: z.string().default(''),
  entities: z.array(z.string()).default([]),
})

export const PlanSchema = z.object({
  complexity: z.enum(['simple', 'multi_hop']),
  in_scope: z.boolean().default(true),
  sub_goals: z.array(SubGoalSchema).default([]),
})

export const ReviewSchema = z.object({
  verdict: z.enum(['pass', 'revise', 'insufficient_evidence']).default('pass'),
  unsupported_claims: z.array(z.string()).default([]),
  ambiguity_flags: z.array(z.string()).default([]),
})

export const ToolCallSchema = z.object({
  tool: z.string(),
  arguments: z.record(z.unknown()).default({}),
  status: z.enum(['ok', 'error', 'timeout']).default('ok'),
})

export const UsageSchema = z.object({
  tokens_in: z.number().default(0),
  tokens_out: z.number().default(0),
})

export const ComparisonCellSchema = z.object({
  text: z.string(),
  citation_ids: z.array(z.string()).default([]),
})

export const ComparisonRowSchema = z.object({
  attribute: z.string(),
  values: z.record(z.string(), ComparisonCellSchema),
})

export const ComparisonSchema = z.object({
  drugs: z.array(z.string()).default([]),
  rows: z.array(ComparisonRowSchema).default([]),
})

export const EgfrThresholdSchema = z.object({
  value: z.number(),
  citation_ids: z.array(z.string()).default([]),
})

export const EgfrWidgetSchema = z.object({
  type: z.literal('egfr').default('egfr'),
  thresholds: z.array(EgfrThresholdSchema).default([]),
})

export const RetrievedChunkSchema = z.object({
  chunk_id: z.string(),
  source_file: z.string(),
  section_path: z.string(),
  excerpt: z.string(),
  dense_rank: z.number().nullable().default(null),
  bm25_rank: z.number().nullable().default(null),
  fused_score: z.number().default(0),
  cited: z.boolean().default(false),
})

export const RetrievalInfoSchema = z.object({
  mode: z.enum(['hybrid', 'bm25_only']),
  candidates: z.number().default(0),
  returned: z.number().default(0),
  chunks: z.array(RetrievedChunkSchema).default([]),
})

export const StageTraceSchema = z.object({
  stage: z.enum(STAGE_NAMES),
  status: z.enum(STAGE_STATUSES).default('done'),
  duration_ms: z.number().nullable().default(null),
  summary: z.string().nullable().default(null),
})

export const AskResponseSchema = z
  .object({
    answer: z.string(),
    sources: z.array(z.string()).default([]),
    citations: z.array(CitationSchema).default([]),
    disclaimer: z.string().default(''),
    plan: PlanSchema.optional(),
    tool_calls: z.array(ToolCallSchema).default([]),
    review: ReviewSchema,
    retrieval_mode: z.enum(['hybrid', 'bm25_only']).default('hybrid'),
    retrieval: RetrievalInfoSchema.nullable().optional(),
    trace: z.array(StageTraceSchema).nullable().optional(),
    trace_id: z.string().default(''),
    usage: UsageSchema.default({ tokens_in: 0, tokens_out: 0 }),
    latency_ms: z.number().default(0),
    comparison: ComparisonSchema.nullable().optional(),
    widgets: z.array(EgfrWidgetSchema).nullable().optional(),
  })
  .passthrough()

export const ApiErrorPayloadSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().nullish(),
  }),
})

export const IndexStatsSchema = z
  .object({
    files: z.number(),
    chunks: z.number(),
    embedding_model: z.string().nullable().default(null),
  })
  .nullable()

export const HealthResponseSchema = z
  .object({
    status: z.string(),
    index: z.enum(['building', 'ready', 'degraded']),
    llm_configured: z.boolean(),
    version: z.string().optional(),
    index_stats: IndexStatsSchema.optional(),
  })
  .passthrough()
