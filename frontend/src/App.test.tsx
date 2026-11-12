import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('always shows the medical disclaimer', () => {
    render(<App />)
    const disclaimer = screen.getByTestId('medical-disclaimer')
    expect(disclaimer).toHaveTextContent(/not medical advice/i)
  })
})
