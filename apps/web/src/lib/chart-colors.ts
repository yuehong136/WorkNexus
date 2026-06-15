import { useUIStore } from '@/stores/ui'

/**
 * Resolve chart colors from the semantic CSS variables in `styles/globals.css`
 * (AGENTS §5.2: charts must read theme tokens via getComputedStyle, never hardcode hex).
 *
 * `useChartColors` subscribes to the ui-store theme so charts recolor on theme switch —
 * the raw CSS variables already reflect the active `data-theme`; reading the theme value
 * only forces a re-render so getComputedStyle is re-evaluated.
 */
const CHART_PALETTE_TOKENS = ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5', 'chart-6', 'chart-7', 'chart-8']

function readVar(token: string): string {
  if (typeof window === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(`--${token}`).trim()
}

export interface ChartColors {
  palette: string[]
  /** Resolve a single semantic token, e.g. `brand-primary`, `status-success`. */
  token: (name: string) => string
  /** Palette color by index (wraps around). */
  at: (index: number) => string
}

export function useChartColors(): ChartColors {
  // Re-render on theme change so the resolved colors stay in sync.
  useUIStore((s) => s.theme)
  const palette = CHART_PALETTE_TOKENS.map(readVar)
  return {
    palette,
    token: readVar,
    at: (index: number) => palette[index % palette.length],
  }
}
