import { describe, expect, it } from 'vitest'

import { countWords, estimateReadingSeconds, formatReadingTime, revealedFraction } from './reading'

function rect(top: number, height: number): DOMRect {
  return {
    x: 0,
    y: top,
    top,
    left: 0,
    right: 0,
    bottom: top + height,
    width: 0,
    height,
    toJSON: () => ({}),
  } as DOMRect
}

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

describe('revealedFraction', () => {
  it('is 0 while the card is still below the scroller bottom', () => {
    expect(revealedFraction(rect(200, 500), rect(0, 100))).toBe(0)
  })

  it('grows as the card scrolls up and clamps to 1', () => {
    expect(revealedFraction(rect(0, 500), rect(0, 100))).toBeCloseTo(0.2)
    expect(revealedFraction(rect(-400, 500), rect(0, 100))).toBe(1)
    expect(revealedFraction(rect(-1000, 500), rect(0, 100))).toBe(1)
  })

  it('returns 0 for a zero-height card', () => {
    expect(revealedFraction(rect(0, 0), rect(0, 100))).toBe(0)
  })
})

