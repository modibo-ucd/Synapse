import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useHistoryStore } from '../stores/history'
import { HistorySidebar } from './HistorySidebar'

describe('HistorySidebar', () => {
  beforeEach(() => {
    window.localStorage.clear()
    useHistoryStore.setState({ sessions: [], activeSessionId: null })
  })

  it('renders the empty state with the privacy note', () => {
    render(<HistorySidebar />)
    expect(screen.getByTestId('history-sidebar')).toBeInTheDocument()
    expect(screen.getByText(/No history yet/)).toBeInTheDocument()
    expect(screen.getByText(/History stays in this browser/)).toBeInTheDocument()
  })

  it('creates a session via the new question button', async () => {
    render(<HistorySidebar />)
    await userEvent.click(screen.getByTestId('history-new-session'))
    expect(useHistoryStore.getState().sessions).toHaveLength(1)
  })

  it('selects, renames and deletes a session', async () => {
    const id = useHistoryStore.getState().newSession()
    useHistoryStore.getState().addTurn(id, 'Warfarin contraindications?')
    render(<HistorySidebar />)

    await userEvent.click(screen.getByTestId(`history-session-button-${id}`))
    expect(useHistoryStore.getState().activeSessionId).toBe(id)

    await userEvent.click(screen.getByTestId(`history-rename-${id}`))
    const input = screen.getByTestId('history-rename-input')
    await userEvent.clear(input)
    await userEvent.type(input, 'Renamed session{Enter}')
    expect(useHistoryStore.getState().sessions[0]!.title).toBe('Renamed session')

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    await userEvent.click(screen.getByTestId(`history-delete-${id}`))
    expect(useHistoryStore.getState().sessions).toHaveLength(0)
    confirmSpy.mockRestore()
  })

  it('clears all history after confirmation', async () => {
    useHistoryStore.getState().newSession()
    useHistoryStore.getState().newSession()
    render(<HistorySidebar />)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    await userEvent.click(screen.getByTestId('history-clear-all'))
    expect(useHistoryStore.getState().sessions).toHaveLength(0)
    confirmSpy.mockRestore()
  })

  it('keeps the session when delete confirmation is cancelled', async () => {
    const id = useHistoryStore.getState().newSession()
    render(<HistorySidebar />)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await userEvent.click(screen.getByTestId(`history-delete-${id}`))
    expect(useHistoryStore.getState().sessions).toHaveLength(1)
    confirmSpy.mockRestore()
  })
})
