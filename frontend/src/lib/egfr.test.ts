import { describe, expect, it } from 'vitest'

import { egfrCkdEpi2021 } from './egfr'

describe('egfrCkdEpi2021', () => {
  it('matches CKD-EPI 2021 reference values', () => {
    expect(egfrCkdEpi2021(30, 'male', 1.0)).toBeCloseTo(103.8, 0)
    expect(egfrCkdEpi2021(60, 'female', 0.8)).toBeCloseTo(84.3, 0)
    expect(egfrCkdEpi2021(60, 'male', 1.0)).toBeCloseTo(86.2, 0)
  })

  it('converts µmol/L to mg/dL', () => {
    expect(egfrCkdEpi2021(60, 'male', 88.4, 'umol_l')).toBeCloseTo(
      egfrCkdEpi2021(60, 'male', 1.0),
      5,
    )
  })
})
