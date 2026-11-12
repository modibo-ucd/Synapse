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
  })
  .passthrough()

export const ApiErrorPayloadSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().nullish(),
  }),
})

export type Citation = z.infer<typeof CitationSchema>
export type Plan = z.infer<typeof PlanSchema>
export type Review = z.infer<typeof ReviewSchema>
export type AskResponse = z.infer<typeof AskResponseSchema>
export type ApiErrorPayload = z.infer<typeof ApiErrorPayloadSchema>
