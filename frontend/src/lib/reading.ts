// Reading-time estimation and formatting. Phase C only needs the label
// helpers; Phase E will reuse these for the progress bar.

const WORDS_PER_MINUTE = 200

/** Counts whitespace-separated words after stripping Markdown syntax. */
export function countWords(markdown: string): number {
  return markdown
    .replace(/[#>*_`|\-[\]()]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length
}

/** ~200 wpm, rounded to the nearest 5 s, with a 5 s floor. */
export function estimateReadingSeconds(markdown: string): number {
  const words = countWords(markdown)
  return Math.max(5, Math.round(words / (WORDS_PER_MINUTE / 60) / 5) * 5)
}

export function formatReadingTime(seconds: number): string {
  return seconds < 60
    ? `${seconds} sec read`
    : `${Math.max(1, Math.round(seconds / 60))} min read`
}
