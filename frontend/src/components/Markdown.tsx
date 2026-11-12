import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

import { citationMarkers } from '../lib/citationMarkers'
import type { Citation } from '../types/api'
import { CitationChip } from './CitationChip'

interface MarkdownProps {
  children: string
  citations?: Citation[]
}

export function Markdown({ children, citations }: MarkdownProps) {
  const citationById = new Map((citations ?? []).map((citation) => [citation.id, citation]))

  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, citationMarkers]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          a: ({ href, children: linkChildren }) => {
            if (href && href.startsWith('#cite-')) {
              const id = href.slice('#cite-'.length)
              return <CitationChip id={id} citation={citationById.get(id)} />
            }
            return <a href={href}>{linkChildren}</a>
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}

