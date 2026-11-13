import { describe, expect, it } from 'vitest'

import { contrastMixed, contrastRatio, hexToRgb, mix, toHex } from './contrast'

// The nine palette hexes (mirrors tailwind.config.ts / index.css).
const NIGHT = '#243341'
const ALABASTER = '#F0F2F5'
const OCEAN = '#205D96'
const STEEL = '#294B6C'
const GLACIAL = '#B5DBFF'
const CREAM = '#FFEDCF'
const SAGE = '#519A76'

const TEXT_MIN = 4.5
const UI_MIN = 3.0

describe('contrast', () => {
  it('computes a WCAG contrast ratio', () => {
    expect(contrastRatio(NIGHT, ALABASTER)).toBeGreaterThan(10)
    expect(contrastRatio(NIGHT, NIGHT)).toBeCloseTo(1, 5)
  })

  it('interpolates sRGB channels like CSS color-mix', () => {
    expect(toHex(mix(NIGHT, ALABASTER, 0.72))).toBe('#5d6873')
    const { r, g, b } = hexToRgb('#000000')
    expect({ r, g, b }).toEqual({ r: 0, g: 0, b: 0 })
  })

  it('keeps text pairs at >= 4.5:1', () => {
    // ink on bg (light theme) and ink on bg (dark theme) are symmetric.
    expect(contrastRatio(NIGHT, ALABASTER)).toBeGreaterThanOrEqual(TEXT_MIN)
    // ink-muted on bg (light): color-mix(night 72%, alabaster).
    expect(contrastMixed(NIGHT, ALABASTER, 0.72, ALABASTER)).toBeGreaterThanOrEqual(TEXT_MIN)
    // ink on card.
    expect(contrastRatio(NIGHT, CREAM)).toBeGreaterThanOrEqual(TEXT_MIN)
    // ink on side (always-dark scope): alabaster text on the night sidebar.
    expect(contrastRatio(ALABASTER, NIGHT)).toBeGreaterThanOrEqual(TEXT_MIN)
    // action-ink on action (primary button).
    expect(contrastRatio(ALABASTER, OCEAN)).toBeGreaterThanOrEqual(TEXT_MIN)
    // badge-ink on badge: light (alabaster on ocean) and dark (glacial on steel).
    expect(contrastRatio(ALABASTER, OCEAN)).toBeGreaterThanOrEqual(TEXT_MIN)
    expect(contrastRatio(GLACIAL, STEEL)).toBeGreaterThanOrEqual(TEXT_MIN)
    // glacial accent on night.
    expect(contrastRatio(GLACIAL, NIGHT)).toBeGreaterThanOrEqual(TEXT_MIN)
  })

  it('keeps UI pairs at >= 3:1 and documents the sage exception', () => {
    // sage is UI-only (dots/icons/large text) per decision 5; it is below text
    // threshold on both surfaces but above the UI threshold.
    expect(contrastRatio(SAGE, NIGHT)).toBeGreaterThanOrEqual(UI_MIN)
    expect(contrastRatio(SAGE, ALABASTER)).toBeGreaterThanOrEqual(UI_MIN)
    expect(contrastRatio(SAGE, NIGHT)).toBeLessThan(TEXT_MIN)
    expect(contrastRatio(SAGE, ALABASTER)).toBeLessThan(TEXT_MIN)
  })
})
