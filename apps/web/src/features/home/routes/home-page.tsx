import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Badge } from '@/components/ui/badge'
import { useHomeQuery } from '@/features/home/api/use-home-query'
import { paths } from '@/lib/paths'
import { cn } from '@/lib/utils'

function HomeCard({
  title,
  total,
  highlight,
  empty,
  children,
  className,
}: {
  title: string
  total: number
  highlight?: boolean
  empty: boolean
  children: ReactNode
  className?: string
}) {
  const { t } = useTranslation('home')
  return (
    <section
      className={cn(
        'rounded-lg border bg-surface-primary p-4',
        highlight ? 'border-brand-primary' : 'border-border-default',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
        <Badge variant={highlight && total > 0 ? 'default' : 'secondary'}>{total}</Badge>
      </div>
      <div className="mt-3 space-y-0.5">
        {empty ? <p className="px-2 py-1.5 text-sm text-text-muted">{t('empty')}</p> : children}
      </div>
    </section>
  )
}

function Row({ to, primary, mono, secondary }: { to: string; primary: string; mono?: boolean; secondary?: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-surface-secondary"
    >
      <span className={cn('truncate text-text-primary', mono ? 'font-mono text-xs' : 'text-sm')}>{primary}</span>
      {secondary ? <span className="shrink-0 text-xs text-text-muted">{secondary}</span> : null}
    </Link>
  )
}

export function HomePage() {
  const { t } = useTranslation('home')
  const query = useHomeQuery()

  if (query.isPending) return <PageSkeleton />
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />

  const s = query.data
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t('title')}</h1>
        <p className="text-sm text-text-muted">{t('subtitle')}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <HomeCard
          title={t('cards.pendingAgentActions')}
          total={s.pendingAgentActions.total}
          highlight
          empty={s.pendingAgentActions.items.length === 0}
          className="lg:col-span-2"
        >
          {s.pendingAgentActions.items.map((action) => (
            <Row key={action.id} to={paths.ai(action.projectId)} primary={action.actionType} mono />
          ))}
        </HomeCard>

        <HomeCard title={t('cards.myTodos')} total={s.myTodos.total} empty={s.myTodos.items.length === 0}>
          {s.myTodos.items.map((item) => (
            <Row key={item.id} to={paths.workItems(item.projectId)} primary={`${item.key} ${item.title}`} />
          ))}
        </HomeCard>

        <HomeCard title={t('cards.overdue')} total={s.overdue.total} empty={s.overdue.items.length === 0}>
          {s.overdue.items.map((item) => (
            <Row
              key={item.id}
              to={paths.workItems(item.projectId)}
              primary={`${item.key} ${item.title}`}
              secondary={t('overdueLabel')}
            />
          ))}
        </HomeCard>

        <HomeCard
          title={t('cards.recentAiCreated')}
          total={s.recentAiCreated.total}
          empty={s.recentAiCreated.items.length === 0}
        >
          {s.recentAiCreated.items.map((item) => (
            <Row key={item.id} to={paths.workItems(item.projectId)} primary={`${item.key} ${item.title}`} />
          ))}
        </HomeCard>

        <HomeCard
          title={t('cards.pendingIntake')}
          total={s.pendingIntake.total}
          empty={s.pendingIntake.items.length === 0}
        >
          {s.pendingIntake.items.map((item) => (
            <Row key={item.id} to={paths.intake(item.projectId)} primary={item.title} />
          ))}
        </HomeCard>
      </div>
    </div>
  )
}
