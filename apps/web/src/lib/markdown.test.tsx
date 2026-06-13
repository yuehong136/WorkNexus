import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Markdown } from '@/lib/markdown'

describe('Markdown', () => {
  it('renders markdown but strips embedded HTML/script', () => {
    const { container } = render(<Markdown content="<script>alert(1)</script>**bold** text" />)
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('strong')?.textContent).toBe('bold')
    expect(container.textContent).not.toContain('alert')
  })

  it('does not emit javascript: links', () => {
    const { container } = render(<Markdown content="[x](javascript:alert(1))" />)
    const href = container.querySelector('a')?.getAttribute('href') ?? ''
    expect(href).not.toContain('javascript:')
  })
})
