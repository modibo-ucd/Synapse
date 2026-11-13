import { sourceTypeFromFileName, sourceTypeLabel } from '../lib/sourceMeta'
import { useUiStore } from '../stores/ui'
import type { Citation, RetrievedChunk } from '../types/api'

interface SourceBadgesProps {
  sources: string[]
  citations: Citation[]
  retrievedChunks: RetrievedChunk[]
}

/** One badge per source file; clicking opens the source modal on that file. */
export function SourceBadges({ sources, citations, retrievedChunks }: SourceBadgesProps) {
  const setSourceView = useUiStore((state) => state.setSourceView)

  const openSource = (fileName: string) => {
    const primary = citations
      .filter((citation) => citation.source_file === fileName)
      .map((citation) => citation.chunk_id)
    const secondary = retrievedChunks
      .filter((chunk) => chunk.source_file === fileName && !chunk.cited)
      .map((chunk) => chunk.chunk_id)
    setSourceView({
      fileName,
      primaryChunkIds: [...new Set(primary)],
      secondaryChunkIds: [...new Set(secondary)],
    })
  }

  return (
    <div data-testid="source-badges" className="flex flex-wrap gap-1.5">
      {sources.map((fileName) => {
        const type = sourceTypeFromFileName(fileName)
        return (
          <button
            key={fileName}
            type="button"
            aria-label={`Open source ${fileName}`}
            title={fileName}
            onClick={() => openSource(fileName)}
            className="inline-flex max-w-full items-center gap-1.5 rounded-full bg-badge px-2 py-0.5 text-xs font-medium text-badge-ink transition-colors hover:bg-action-hover"
          >
            <span className="truncate font-mono">{fileName}</span>
            <span className="shrink-0 opacity-80">{sourceTypeLabel(type)}</span>
          </button>
        )
      })}
    </div>
  )
}
