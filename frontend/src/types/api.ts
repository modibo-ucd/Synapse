import { z } from 'zod'

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
  status: z.enum(['ok', 'error']).default('ok'),
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
    trace_id: z.string().default(''),
    usage: UsageSchema.default({ tokens_in: 0, tokens_out: 0 }),
    latency_ms: z.number().default(0),
    comparison: ComparisonSchema.nullable().optional(),
  })
  .passthrough()

export const ApiErrorPayloadSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().nullish(),
  }),
})

export const StageEventDetailsSchema = z.object({
  complexity: z.string().optional(),
  in_scope: z.boolean().optional(),
  sub_goals: z.array(SubGoalSchema).optional(),
  mode: z.string().optional(),
  chunk_count: z.number().optional(),
  source_files: z.array(z.string()).optional(),
  chunks: z
    .array(
      z.object({
        source_file: z.string(),
        section: z.string(),
        dense_rank: z.number().nullable().optional(),
        bm25_rank: z.number().nullable().optional(),
        fused_score: z.number().optional(),
      }),
    )
    .optional(),
  claims: z.number().optional(),
  tool_calls: z.array(ToolCallSchema).optional(),
  verdict: z.string().optional(),
  unsupported_claims: z.array(z.string()).optional(),
  ambiguity_flags: z.array(z.string()).optional(),
  sources: z.array(z.string()).optional(),
})

export const StageEventSchema = z.object({
  stage: z.enum(['plan', 'retrieve', 'tools', 'review', 'answer']),
  status: z.enum(['ok', 'skipped']).default('ok'),
  duration_ms: z.number().default(0),
  summary: z.string().default(''),
  details: StageEventDetailsSchema.default({}),
})

export type Citation = z.infer<typeof CitationSchema>
export type Plan = z.infer<typeof PlanSchema>
export type Review = z.infer<typeof ReviewSchema>
export type AskResponse = z.infer<typeof AskResponseSchema>
export type ApiErrorPayload = z.infer<typeof ApiErrorPayloadSchema>
export type StageEvent = z.infer<typeof StageEventSchema>
export type Comparison = z.infer<typeof ComparisonSchema>
