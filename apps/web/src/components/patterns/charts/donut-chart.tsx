import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { type CategoryDatum, TOOLTIP_CONTENT_STYLE, TOOLTIP_LABEL_STYLE } from './chart-primitives'

export function DonutChart({ data, height = 200 }: { data: CategoryDatum[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="label"
          innerRadius="55%"
          outerRadius="85%"
          paddingAngle={2}
          stroke="none"
        >
          {data.map((d) => (
            <Cell key={d.label} fill={d.color} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_CONTENT_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
      </PieChart>
    </ResponsiveContainer>
  )
}
