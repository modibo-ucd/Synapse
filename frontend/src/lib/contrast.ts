// WCAG 2.x contrast ratio + an sRGB `color-mix` helper (linear interpolation of
// 0-255 channels). Used by the contrast test to enforce the palette's contrast.

export interface Rgb {
  r: number
  g: number
  b: number
}

export function hexToRgb(hex: string): Rgb {
  const value = hex.replace('#', '')
  const expanded =
    value.length === 3
      ? value
          .split('')
          .map((c) => c + c)
          .join('')
      : value
  return {
    r: parseInt(expanded.slice(0, 2), 16),
    g: parseInt(expanded.slice(2, 4), 16),
    b: parseInt(expanded.slice(4, 6), 16),
  }
}

function channelToLinear(channel: number): number {
  const value = channel / 255
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
}

export function relativeLuminance(rgb: Rgb): number {
  return (
    0.2126 * channelToLinear(rgb.r) +
    0.7152 * channelToLinear(rgb.g) +
    0.0722 * channelToLinear(rgb.b)
  )
}

export function contrastRatio(hexA: string, hexB: string): number {
  const luminanceA = relativeLuminance(hexToRgb(hexA))
  const luminanceB = relativeLuminance(hexToRgb(hexB))
  const lighter = Math.max(luminanceA, luminanceB)
  const darker = Math.min(luminanceA, luminanceB)
  return (lighter + 0.05) / (darker + 0.05)
}

/** Linear interpolation of two sRGB colors, mirroring CSS `color-mix`. */
export function mix(hexA: string, hexB: string, weightA = 0.5): Rgb {
  const a = hexToRgb(hexA)
  const b = hexToRgb(hexB)
  const weight = Math.min(1, Math.max(0, weightA))
  const channel = (x: number, y: number) => Math.round(x * weight + y * (1 - weight))
  return { r: channel(a.r, b.r), g: channel(a.g, b.g), b: channel(a.b, b.b) }
}

export function toHex(rgb: Rgb): string {
  const hex = (channel: number) => channel.toString(16).padStart(2, '0')
  return `#${hex(rgb.r)}${hex(rgb.g)}${hex(rgb.b)}`
}

/** Contrast of `weightA`×`hexA` mixed with `hexB`, against a background. */
export function contrastMixed(
  hexA: string,
  hexB: string,
  weightA: number,
  background: string,
): number {
  return contrastRatio(toHex(mix(hexA, hexB, weightA)), background)
}
