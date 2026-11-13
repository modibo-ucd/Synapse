import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { StickyAskBar } from './StickyAskBar'

function Harness({
  onSubmit,
  pending = false,
  disabledReason = null,
}: {
  onSubmit: (question: string) => void
  pending?: boolean
  disabledReason?: string | null
}) {
  const [value, setValue] = useState('')
  return (
    <StickyAskBar
      value={value}
      onChange={setValue}
      onSubmit={onSubmit}
      onStop={() => {}}
      pending={pending}
      disabledReason={disabledReason}
    />
  )
}

describe('StickyAskBar', () => {
  it('submits on Enter', async () => {
    const onSubmit = vi.fn()
    render(<Harness onSubmit={onSubmit} />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin{Enter}')
    expect(onSubmit).toHaveBeenCalledWith('warfarin')
  })

  it('does not submit on Shift+Enter', async () => {
    const onSubmit = vi.fn()
    render(<Harness onSubmit={onSubmit} />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin{Shift>}{Enter}{/Shift}')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows the character counter past 1800 characters', () => {
    render(
      <StickyAskBar
        value={'x'.repeat(1800)}
        onChange={() => {}}
        onSubmit={() => {}}
        onStop={() => {}}
        pending={false}
      />,
    )
    expect(screen.getByTestId('ask-bar-hint')).toHaveTextContent('1800/2000')
  })

  it('shows a Stop button while pending', () => {
    render(<Harness onSubmit={() => {}} pending />)
    expect(screen.getByTestId('stop-button')).toBeInTheDocument()
    expect(screen.queryByTestId('submit-button')).not.toBeInTheDocument()
  })

  it('disables the bar with a reason when the API is unreachable', () => {
    render(<Harness onSubmit={() => {}} disabledReason="The API is unreachable" />)
    expect(screen.getByTestId('question-input')).toBeDisabled()
    expect(screen.getByTestId('submit-button')).toBeDisabled()
    expect(screen.getByTestId('ask-bar-disabled-reason')).toHaveTextContent('The API is unreachable')
  })

  it('always shows the not-medical-advice caption', () => {
    render(<Harness onSubmit={() => {}} />)
    expect(screen.getByTestId('ask-bar-caption')).toHaveTextContent(/Not medical advice/)
  })
})
