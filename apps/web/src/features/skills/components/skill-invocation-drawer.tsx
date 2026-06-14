import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorState } from '@/components/patterns/error-state'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { useSkillInvocationQuery } from '@/features/skills/api/use-skill-invocation-query'
import { formatDateTime } from '@/lib/datetime'

import { InvocationStatusBadge, RiskBadge } from './skill-badges'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-text-muted">{label}</p>
      <div className="text-sm text-text-primary">{children}</div>
    </div>
  )
}

function Summary({ value }: { value: string | null }) {
  if (!value) return <span className="text-text-muted">—</span>
  return (
    <pre className="max-h-48 overflow-auto rounded-md bg-surface-secondary p-2 text-xs whitespace-pre-wrap text-text-secondary">
      {value}
    </pre>
  )
}

function DrawerBody({ invocationId }: { invocationId: string }) {
  const { t } = useTranslation('skills')
  const query = useSkillInvocationQuery(invocationId)

  if (query.isPending) return <Skeleton className="h-64 w-full" />
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />

  const inv = query.data
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label={t('columns.tool')}>
          <span className="font-mono text-xs">{inv.toolName}</span>
        </Field>
        <Field label={t('columns.skill')}>
          <span className="font-mono text-xs">{inv.skillCode}</span>
        </Field>
        <Field label={t('columns.risk')}>
          <RiskBadge risk={inv.riskLevel} />
        </Field>
        <Field label={t('columns.status')}>
          <InvocationStatusBadge status={inv.status} />
        </Field>
        <Field label={t('detail.representedUser')}>{inv.representedUser?.displayName ?? t('common.none')}</Field>
        <Field label={t('detail.callerType')}>{inv.callerType}</Field>
        <Field label={t('detail.project')}>{inv.projectId ?? t('common.none')}</Field>
        <Field label={t('detail.conversation')}>{inv.conversationId ?? t('common.none')}</Field>
        <Field label={t('detail.run')}>{inv.runId ?? t('common.none')}</Field>
        <Field label={t('detail.requiresConfirmation')}>
          {inv.requiresConfirmation ? t('common.yes') : t('common.no')}
        </Field>
        <Field label={t('detail.agentAction')}>{inv.agentActionId ?? t('common.none')}</Field>
        <Field label={t('detail.startedAt')}>{formatDateTime(inv.startedAt)}</Field>
        <Field label={t('detail.finishedAt')}>{formatDateTime(inv.finishedAt)}</Field>
      </div>
      <Field label={t('detail.inputSummary')}>
        <Summary value={inv.inputSummary} />
      </Field>
      <Field label={t('detail.outputSummary')}>
        <Summary value={inv.outputSummary} />
      </Field>
      {inv.errorMessage ? (
        <Field label={t('detail.error')}>
          <Summary value={inv.errorMessage} />
        </Field>
      ) : null}
    </div>
  )
}

export function SkillInvocationDrawer({
  invocationId,
  open,
  onOpenChange,
}: {
  invocationId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation('skills')
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{t('detail.title')}</SheetTitle>
          <SheetDescription className="sr-only">{t('detail.title')}</SheetDescription>
        </SheetHeader>
        {invocationId ? <DrawerBody invocationId={invocationId} /> : null}
      </SheetContent>
    </Sheet>
  )
}
