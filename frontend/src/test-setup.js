import { vi } from 'vitest'
import '@testing-library/jest-dom'

// EventSource is not available in jsdom — provide a minimal stub
global.EventSource = vi.fn(() => ({
  onmessage: null,
  onerror: null,
  close: vi.fn(),
}))
