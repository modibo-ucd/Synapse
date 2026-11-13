import { useMemo } from 'react'
import type { Element } from 'hast'
import { defaultSchema } from 'hast-util-sanitize'
import type { Schema } from 'hast-util-sanitize'
import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

import { rehypeCitations } from '../lib/markdown/rehypeCitations'
import { rehypeSourceHighlight, type HighlightRange } from '../lib/markdown/rehypeSourceHighlight'
import type { Citation } from '../types/api'
import { CitationChip } from './CitationChip'

const sanitizeSchema: Schema = (() => {
  const attributes = defaultSchema.attributes ?? {}
  return {
    ...defaultSchema,
    attributes: {
      ...attributes,
      '*': [...(attributes['*'] ?? []), 'dataHighlight'],
    },
  }
})()

interface SafeMarkdownProps {
  children: string
  className?: string
  highlightRanges?: HighlightRange[]
  citations?: Citation[]
  onOpenCitation?: (citation: Citation) => void
}

function readCitationId(node: Element | undefined): string {
  if (!node) return ''
  const id = node.properties.dataCitationId
  return typeof id === 'string' ? id : ''
}

/**
 * Sanitized Markdown renderer. Plugin order is fixed:
 * source highlight -> sanitize (extended schema) -> citation chips.
 */
export function SafeMarkdown({
  children,
  className,
  highlightRanges,
  citations,
  onOpenCitation,
}: SafeMarkdownProps) {
  const citationById = useMemo(
    () => new Map((citations ?? []).map((citation) => [citation.id, citation])),
    [citations],
  )

  const components = {
    'cite-chip': ({ node }: { node?: Element }) => {
      const id = readCitationId(node)
      return <CitationChip id={id} citation={citationById.get(id)} onOpen={onOpenCitation} />
    },
  } as unknown as Components

  return (
    <div className={className ?? 'prose-synapse prose max-w-none'}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[
          [rehypeSourceHighlight, { ranges: highlightRanges ?? [] }],
          [rehypeSanitize, sanitizeSchema],
          rehypeCitations,
        ]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
