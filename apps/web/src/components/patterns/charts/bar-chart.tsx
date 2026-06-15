import { Bar, BarChart as ReBarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { type CategoryDatum, TOOLTIP_CONTENT_STYLE, TOOLTIP_LABEL_STYLE } from './chart-primitives'

/** Horizontal categorical bars — labels read better on the Y axis for many categories. */
export function BarChart({
  data,
  axisColor,
  height = 200,
}: {
  data: CategoryDatum[]
  axisColor: string
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReBarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
        <YAxis
          type="category"
          dataKey="label"
          width={84}
          tick={{ fontSize: 12, fill: axisColor }}
          stroke={axisColor}
        />
        <Tooltip
          cursor={{ fill: 'var(--surface-secondary)' }}
          contentStyle={TOOLTIP_CONTENT_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((d) => (
            <Cell key={d.label} fill={d.color} />
          ))}
        </Bar>
      </ReBarChart>
    </ResponsiveContainer>
  )
}
