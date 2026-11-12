import type { Citation } from '../types/api'

interface SourcesListProps {
  sources: string[]
  citations: Citation[]
}

interface SourceEntry {
  key: string
  file: string
  section: string
}

export function SourcesList({ sources, citations }: SourcesListProps) {
  const entries: SourceEntry[] =
    citations.length > 0
      ? citations.map((citation) => ({
          key: citation.id,
          file: citation.source_file,
          section: citation.section,
        }))
      : sources.map((file, index) => ({ key: `src-${index}`, file, section: '' }))

  if (entries.length === 0) {
    return null
  }

  return (
    <section data-testid="sources-list" aria-label="Sources" className="mt-6 border-t border-slate-200 pt-4">
      <h3 className="text-sm font-semibold text-slate-700">Sources</h3>
      <ul className="mt-2 space-y-1">
        {entries.map((entry) => (
          <li
            key={entry.key}
            id={`cite-source-${entry.key}`}
            className="scroll-mt-24 text-sm text-slate-600 transition-colors duration-500"
          >
            <span className="font-medium text-slate-800">{entry.file}</span>
            {entry.section ? <span className="text-slate-500"> · {entry.section}</span> : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
