import { describe, expect, it } from 'vitest'

import { cn } from '@/lib/utils'

describe('cn', () => {
  it('merges conditional class names', () => {
    const hidden = [] as string[]
    expect(cn('a', hidden.length > 0 && 'b', 'c')).toBe('a c')
  })

  it('resolves tailwind conflicts with the last value', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })
})
