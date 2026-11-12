import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { Citation, EgfrWidget } from '../types/api'
import { EgfrCalculator } from './EgfrCalculator'

const widget: EgfrWidget = {
  type: 'egfr',
  thresholds: [
    { value: 30, citation_ids: ['S1'] },
    { value: 45, citation_ids: [] },
  ],
}

const citations: Citation[] = [
  {
    id: 'S1',
    source_file: 'dailymed-metformin.md',
    section: '4 CONTRAINDICATIONS',
    chunk_id: 'c1',
    excerpt: 'eGFR below 30',
  },
]

describe('EgfrCalculator', () => {
  it('shows the estimated eGFR and the disclaimer', () => {
    render(<EgfrCalculator widget={widget} citations={citations} />)
    expect(screen.getByTestId('egfr-result')).toHaveTextContent('86')
    expect(screen.getByText(/not personalized dosing advice/i)).toBeInTheDocument()
  })

  it('updates the result when inputs change', () => {
    render(<EgfrCalculator widget={widget} citations={citations} />)
    fireEvent.change(screen.getByTestId('egfr-age'), { target: { value: '30' } })
    expect(screen.getByTestId('egfr-result')).toHaveTextContent('103')
  })

  it('flags thresholds the result crosses', () => {
    render(<EgfrCalculator widget={widget} citations={citations} />)
    fireEvent.change(screen.getByTestId('egfr-creatinine'), { target: { value: '3.0' } })
    expect(screen.getByTestId('egfr-threshold-30')).toHaveTextContent('Below 30')
    expect(screen.getByTestId('egfr-threshold-45')).toHaveTextContent('Below 45')
  })
})
