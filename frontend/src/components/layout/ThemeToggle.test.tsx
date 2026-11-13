import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useSettingsStore } from '../../stores/settings'
import { ThemeToggle } from './ThemeToggle'

function resetThemeMeta() {
  document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => meta.remove())
  const meta = document.createElement('meta')
  meta.name = 'theme-color'
  meta.content = '#F0F2F5'
  document.head.appendChild(meta)
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    window.localStorage.clear()
    useSettingsStore.setState({
      theme: 'system',
      haptics: true,
      historyOpen: true,
      traceOpen: true,
    })
    document.documentElement.classList.remove('dark')
    resetThemeMeta()
  })

  afterEach(() => {
    document.documentElement.classList.remove('dark')
  })

  it('toggles the dark class and theme-color meta, and persists the choice', async () => {
    render(<ThemeToggle />)
    const button = screen.getByTestId('theme-toggle')

    expect(button).toHaveAttribute('aria-pressed', 'false')
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    await userEvent.click(button)

    expect(button).toHaveAttribute('aria-pressed', 'true')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe(
      '#243341',
    )
    expect(useSettingsStore.getState().theme).toBe('dark')
    expect(window.localStorage.getItem('synapse.theme')).toBe('dark')
    expect(window.localStorage.getItem('synapse.settings')).toContain('dark')
  })

  it('toggles back to light', async () => {
    useSettingsStore.setState({ theme: 'dark' })
    render(<ThemeToggle />)
    const button = screen.getByTestId('theme-toggle')

    expect(document.documentElement.classList.contains('dark')).toBe(true)

    await userEvent.click(button)

    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe(
      '#F0F2F5',
    )
  })
})
