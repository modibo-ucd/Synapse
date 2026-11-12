import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Citation, Comparison } from '../types/api'
import { ComparisonMatrix } from './ComparisonMatrix'

const comparison: Comparison = {
  drugs: ['apixaban', 'warfarin'],
  rows: [
    {
      attribute: 'contraindications',
      values: {
        apixaban: { text: 'active pathological bleeding', citation_ids: ['S1'] },
        warfarin: { text: 'pregnancy', citation_ids: ['S2'] },
      },
    },
    {
      attribute: 'monitoring',
      values: {
        apixaban: { text: 'Not stated in sources', citation_ids: [] },
        warfarin: { text: 'INR', citation_ids: ['S2'] },
      },
    },
  ],
}

const citations: Citation[] = [
  {
    id: 'S1',
    source_file: 'dailymed-apixaban.md',
    section: '4 CONTRAINDICATIONS',
    chunk_id: 'c1',
    excerpt: 'active pathological bleeding',
  },
  {
    id: 'S2',
    source_file: 'dailymed-warfarin.md',
    section: '4 CONTRAINDICATIONS',
    chunk_id: 'c2',
    excerpt: 'pregnancy',
  },
]

describe('ComparisonMatrix', () => {
  it('renders a grid with attribute rows and drug columns', () => {
    render(<ComparisonMatrix comparison={comparison} citations={citations} />)
    expect(screen.getByRole('columnheader', { name: 'apixaban' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'warfarin' })).toBeInTheDocument()
    expect(screen.getByText('Contraindications')).toBeInTheDocument()
    expect(screen.getByText('Monitoring')).toBeInTheDocument()
  })

  it('filters rows by attribute text', async () => {
    render(<ComparisonMatrix comparison={comparison} citations={citations} />)
    await userEvent.type(screen.getByTestId('comparison-filter'), 'monitoring')
    expect(screen.getByText('Monitoring')).toBeInTheDocument()
    expect(screen.queryByText('Contraindications')).not.toBeInTheDocument()
  })

  it('renders citation chips inside cells', () => {
    render(<ComparisonMatrix comparison={comparison} citations={citations} />)
    expect(screen.getAllByTestId('citation-S1').length).toBeGreaterThan(0)
    expect(screen.getByText('Not stated in sources')).toBeInTheDocument()
  })
})
