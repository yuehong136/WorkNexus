import {
  CartesianGrid,
  Legend,
  Line,
  LineChart as ReLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { type TrendSeries, TOOLTIP_CONTENT_STYLE, TOOLTIP_LABEL_STYLE } from './chart-primitives'

export function LineChart({
  data,
  xKey,
  series,
  axisColor,
  gridColor,
  height = 220,
}: {
  data: Record<string, unknown>[]
  xKey: string
  series: TrendSeries[]
  axisColor: string
  gridColor: string
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReLineChart data={data} margin={{ left: 4, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: axisColor }} stroke={axisColor} />
        <YAxis allowDecimals={false} width={28} tick={{ fontSize: 11, fill: axisColor }} stroke={axisColor} />
        <Tooltip contentStyle={TOOLTIP_CONTENT_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s) => (
          <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={false} />
        ))}
      </ReLineChart>
    </ResponsiveContainer>
  )
}
