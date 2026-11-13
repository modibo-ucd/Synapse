import { useState } from 'react'

import type { Citation, Comparison } from '../types/api'
import { CitationChip } from './CitationChip'

interface ComparisonMatrixProps {
  comparison: Comparison
  citations: Citation[]
}

function formatAttribute(attribute: string): string {
  return attribute.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

export function ComparisonMatrix({ comparison, citations }: ComparisonMatrixProps) {
  const [filter, setFilter] = useState('')
  const citationById = new Map(citations.map((citation) => [citation.id, citation]))
  const rows = comparison.rows.filter((row) =>
    row.attribute.toLowerCase().includes(filter.trim().toLowerCase()),
  )

  return (
    <section
      data-testid="comparison-matrix"
      aria-label="Drug comparison"
      className="mt-6 border-t border-line pt-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">Comparison</h3>
        <label className="flex items-center gap-2 text-xs text-ink-muted">
          Filter
          <input
            type="text"
            data-testid="comparison-filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="e.g. contraindications"
            className="rounded border border-line px-2 py-1 text-xs text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
      </div>

      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 bg-surface px-2 py-1 text-left font-semibold text-ink"
              >
                Attribute
              </th>
              {comparison.drugs.map((drug) => (
                <th
                  key={drug}
                  scope="col"
                  className="px-2 py-1 text-left font-semibold text-ink"
                >
                  {drug}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.attribute}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-surface px-2 py-1.5 text-left align-top font-medium text-ink"
                >
                  {formatAttribute(row.attribute)}
                </th>
                {comparison.drugs.map((drug) => {
                  const cell = row.values[drug]
                  return (
                    <td
                      key={drug}
                      className="border-t border-line px-2 py-1.5 align-top text-ink-muted"
                    >
                      {cell ? (
                        <>
                          {cell.text}
                          {cell.citation_ids.map((id) => (
                            <CitationChip key={id} id={id} citation={citationById.get(id)} />
                          ))}
                        </>
                      ) : (
                        'Not stated in sources'
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
