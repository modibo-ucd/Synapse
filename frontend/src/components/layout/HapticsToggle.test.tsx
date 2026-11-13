import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { HapticsToggle } from './HapticsToggle'
import { useSettingsStore } from '../../stores/settings'

describe('HapticsToggle', () => {
  beforeEach(() => {
    useSettingsStore.setState({ haptics: true })
  })

  it('reflects the setting and toggles it on click', async () => {
    const user = userEvent.setup()
    render(<HapticsToggle />)
    const button = screen.getByTestId('haptics-toggle')
    expect(button).toHaveAttribute('aria-pressed', 'true')
    await user.click(button)
    expect(useSettingsStore.getState().haptics).toBe(false)
    expect(button).toHaveAttribute('aria-pressed', 'false')
  })
})
