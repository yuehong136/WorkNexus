import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useChartColors } from '@/lib/chart-colors'

describe('useChartColors', () => {
  it('exposes an 8-color palette and wraps the index', () => {
    const { result } = renderHook(() => useChartColors())
    expect(result.current.palette).toHaveLength(8)
    // at() wraps around the palette length
    expect(result.current.at(8)).toBe(result.current.at(0))
    expect(result.current.at(9)).toBe(result.current.at(1))
    // token() reads a CSS variable without throwing
    expect(typeof result.current.token('text-muted')).toBe('string')
  })
})
