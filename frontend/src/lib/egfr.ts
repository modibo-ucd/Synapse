export type Sex = 'male' | 'female'
export type CreatinineUnit = 'mg_dl' | 'umol_l'

const UMOL_PER_MGDL = 88.4

// CKD-EPI 2021 creatinine equation (race-free), mirrored from the backend so the
// widget can compute the estimate live without an extra round-trip.
export function egfrCkdEpi2021(
  age: number,
  sex: Sex,
  serumCreatinine: number,
  unit: CreatinineUnit = 'mg_dl',
): number {
  const scr = unit === 'umol_l' ? serumCreatinine / UMOL_PER_MGDL : serumCreatinine
  const kappa = sex === 'female' ? 0.7 : 0.9
  const alpha = sex === 'female' ? -0.241 : -0.302
  const ratio = scr / kappa
  let egfr = 142 * Math.min(ratio, 1) ** alpha * Math.max(ratio, 1) ** -1.2 * 0.9938 ** age
  if (sex === 'female') {
    egfr *= 1.012
  }
  return Math.round(egfr * 10) / 10
}
