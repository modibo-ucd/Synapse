import { describe, expect, it } from 'vitest'

import { countWords, estimateReadingSeconds, formatReadingTime } from './reading'

describe('reading helpers', () => {
  it('counts words and ignores markdown syntax', () => {
    expect(countWords('# Hello **bold** world')).toBe(3)
    expect(countWords('')).toBe(0)
    expect(countWords('| a | b |\n| - | - |\n| 1 | 2 |')).toBe(4)
  })

  it('estimates at ~200 wpm with a 5s floor and 5s rounding', () => {
    expect(estimateReadingSeconds('one word')).toBe(5)
    expect(estimateReadingSeconds(Array(200).fill('word').join(' '))).toBe(60)
  })

  it('formats reading time labels', () => {
    expect(formatReadingTime(5)).toBe('5 sec read')
    expect(formatReadingTime(60)).toBe('1 min read')
    expect(formatReadingTime(120)).toBe('2 min read')
  })
})
