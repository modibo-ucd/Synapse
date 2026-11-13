import type { SourceDocType } from '../types/api'

/** Derives the source kind from a corpus file name. */
export function sourceTypeFromFileName(fileName: string): SourceDocType {
  const lower = fileName.toLowerCase()
  if (lower === 'glossary.md') return 'glossary'
  if (lower.startsWith('dailymed-')) return 'dailymed'
  if (lower.startsWith('medlineplus-')) return 'medlineplus'
  return 'dailymed'
}

/** Human-readable label for a source kind. */
export function sourceTypeLabel(type: SourceDocType): string {
  switch (type) {
    case 'dailymed':
      return 'DailyMed'
    case 'medlineplus':
      return 'MedlinePlus'
    case 'glossary':
      return 'Glossary'
  }
}
