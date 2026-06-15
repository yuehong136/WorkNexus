/** Shared shapes for the chart wrappers. Colors are passed in already resolved from
 * semantic CSS tokens (see lib/chart-colors.ts) — patterns never read tokens themselves. */

export interface CategoryDatum {
  label: string
  value: number
  color: string
}

export interface TrendSeries {
  key: string
  label: string
  color: string
}

// CSS-var references (resolved live by the browser, theme-reactive, never hardcoded hex).
export const TOOLTIP_CONTENT_STYLE = {
  backgroundColor: 'var(--surface-raised)',
  border: '1px solid var(--border-default)',
  borderRadius: '8px',
  fontSize: '12px',
  color: 'var(--text-primary)',
  boxShadow: 'none',
} as const

export const TOOLTIP_LABEL_STYLE = { color: 'var(--text-secondary)' } as const
