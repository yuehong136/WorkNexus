import { describe, expect, it } from 'vitest'

import { memberAddSchema, projectCreateSchema } from '@/features/projects/api/schemas'
import type { AppTFunction } from '@/locales/i18n'

// The schemas only call t() for messages; a passthrough stub is enough here.
const t = ((key: string) => key) as unknown as AppTFunction

describe('projectCreateSchema', () => {
  const schema = projectCreateSchema(t)

  it('accepts a valid name and key', () => {
    expect(schema.safeParse({ name: 'Beta', key: 'BETA' }).success).toBe(true)
  })

  it('rejects a key that is too short or has invalid characters', () => {
    expect(schema.safeParse({ name: 'Beta', key: 'B' }).success).toBe(false)
    expect(schema.safeParse({ name: 'Beta', key: 'be ta' }).success).toBe(false)
  })

  it('rejects an empty name', () => {
    expect(schema.safeParse({ name: '', key: 'BETA' }).success).toBe(false)
  })
})

describe('memberAddSchema', () => {
  const schema = memberAddSchema(t)

  it('requires a user id and a valid role', () => {
    expect(schema.safeParse({ userId: 'u1', role: 'member' }).success).toBe(true)
    expect(schema.safeParse({ userId: '', role: 'member' }).success).toBe(false)
    expect(schema.safeParse({ userId: 'u1', role: 'owner' }).success).toBe(false)
  })
})
