import { describe, expect, it } from 'vitest'

import { applyTheme, useUIStore } from '@/stores/ui'

describe('theme', () => {
  it('applyTheme sets data-theme on documentElement', () => {
    applyTheme('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    applyTheme('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('system theme resolves via matchMedia', () => {
    applyTheme('system')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('setTheme updates store state and DOM together', () => {
    useUIStore.getState().setTheme('dark')
    expect(useUIStore.getState().theme).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })
})
