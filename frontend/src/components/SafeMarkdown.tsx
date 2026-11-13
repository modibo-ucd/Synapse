import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

interface SafeMarkdownProps {
  children: string
  className?: string
}

/**
 * Sanitized Markdown renderer. `rehype-sanitize` strips dangerous HTML and
 * `javascript:` links; nothing here uses `dangerouslySetInnerHTML`. Citation
 * chip rewriting is added in Phase D (rehypeCitations).
 */
export function SafeMarkdown({ children, className }: SafeMarkdownProps) {
  return (
    <div className={className ?? 'prose prose-synapse max-w-none'}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
