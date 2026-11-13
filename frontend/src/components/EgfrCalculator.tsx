import { useMemo, useState } from 'react'

import { egfrCkdEpi2021, type CreatinineUnit, type Sex } from '../lib/egfr'
import type { Citation, EgfrWidget } from '../types/api'
import { CitationChip } from './CitationChip'

interface EgfrCalculatorProps {
  widget: EgfrWidget
  citations: Citation[]
}

export function EgfrCalculator({ widget, citations }: EgfrCalculatorProps) {
  const [age, setAge] = useState('60')
  const [sex, setSex] = useState<Sex>('male')
  const [creatinine, setCreatinine] = useState('1.0')
  const [unit, setUnit] = useState<CreatinineUnit>('mg_dl')

  const citationById = new Map(citations.map((citation) => [citation.id, citation]))

  const result = useMemo(() => {
    const ageNumber = Number(age)
    const creatinineNumber = Number(creatinine)
    if (!Number.isFinite(ageNumber) || ageNumber < 18 || ageNumber > 120) {
      return null
    }
    if (!Number.isFinite(creatinineNumber) || creatinineNumber <= 0) {
      return null
    }
    return egfrCkdEpi2021(ageNumber, sex, creatinineNumber, unit)
  }, [age, sex, creatinine, unit])

  return (
    <section
      data-testid="egfr-widget"
      aria-label="eGFR estimator"
      className="mt-6 border-t border-line pt-4"
    >
      <h3 className="text-sm font-semibold text-ink">eGFR estimator</h3>
      <p className="text-xs text-ink-muted">
        Educational estimate only. Always consult a healthcare professional — this is not
        personalized dosing advice.
      </p>

      <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs text-ink-muted">
          Age (years)
          <input
            type="number"
            data-testid="egfr-age"
            value={age}
            onChange={(event) => setAge(event.target.value)}
            min={18}
            max={120}
            className="rounded border border-line px-2 py-1 text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-ink-muted">
          Sex
          <select
            data-testid="egfr-sex"
            value={sex}
            onChange={(event) => setSex(event.target.value as Sex)}
            className="rounded border border-line px-2 py-1 text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-ink-muted">
          Serum creatinine
          <input
            type="number"
            data-testid="egfr-creatinine"
            value={creatinine}
            onChange={(event) => setCreatinine(event.target.value)}
            min={0.1}
            step="0.1"
            className="rounded border border-line px-2 py-1 text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-ink-muted">
          Unit
          <select
            data-testid="egfr-unit"
            value={unit}
            onChange={(event) => setUnit(event.target.value as CreatinineUnit)}
            className="rounded border border-line px-2 py-1 text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            <option value="mg_dl">mg/dL</option>
            <option value="umol_l">µmol/L</option>
          </select>
        </label>
      </div>

      {result !== null && (
        <p data-testid="egfr-result" className="mt-3 text-sm font-semibold text-ink">
          Estimated eGFR: {result} mL/min/1.73 m²
        </p>
      )}

      {widget.thresholds.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Cited eGFR thresholds">
          {widget.thresholds.map((threshold) => {
            const crossed = result !== null && result < threshold.value
            return (
              <li
                key={threshold.value}
                data-testid={`egfr-threshold-${threshold.value}`}
                className={`rounded-full border px-2 py-1 text-xs ${
                  crossed
                    ? 'border-champagne bg-champagne/40 text-ink'
                    : 'border-line bg-surface text-ink-muted'
                }`}
              >
                {crossed ? 'Below' : 'Above'} {threshold.value}
                {threshold.citation_ids.map((id) => (
                  <CitationChip key={id} id={id} citation={citationById.get(id)} />
                ))}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
