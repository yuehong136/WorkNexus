import type { AuditLogOut } from '@worknexus/contracts'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { formatDateTime } from '@/lib/datetime'
import { paths } from '@/lib/paths'

import { ActorBadge } from './audit-badges'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-text-muted">{label}</p>
      <div className="text-sm text-text-primary">{children}</div>
    </div>
  )
}

function Json({ value }: { value: unknown }) {
  if (value == null) return <span className="text-text-muted">—</span>
  return (
    <pre className="max-h-48 overflow-auto rounded-md bg-surface-secondary p-2 text-xs whitespace-pre-wrap text-text-secondary">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

function skillInvocationId(detail: AuditLogOut['detail']): string | null {
  if (detail && typeof detail === 'object' && 'skillInvocationId' in detail) {
    const value = (detail as Record<string, unknown>).skillInvocationId
    return typeof value === 'string' ? value : null
  }
  return null
}

function Body({ log, onViewChain }: { log: AuditLogOut; onViewChain: (type: string, id: string) => void }) {
  const { t } = useTranslation('audit')
  const skillId = skillInvocationId(log.detail)
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label={t('columns.time')}>{formatDateTime(log.createdAt)}</Field>
        <Field label={t('detail.actor')}>
          <ActorBadge type={log.actor.type} name={log.actor.displayName} />
        </Field>
        <Field label={t('detail.action')}>
          <span className="font-mono text-xs">{log.action}</span>
        </Field>
        <Field label={t('detail.resource')}>
          <span className="font-mono text-xs">
            {log.resourceType}
            {log.resourceId ? `:${log.resourceId}` : ''}
          </span>
        </Field>
        <Field label={t('detail.project')}>{log.projectName ?? t('detail.none')}</Field>
        <Field label={t('detail.requestId')}>
          <span className="font-mono text-xs">{log.requestId ?? t('detail.none')}</span>
        </Field>
        <Field label={t('detail.ipAddress')}>{log.ipAddress ?? t('detail.none')}</Field>
      </div>

      {skillId ? (
        <Field label={t('detail.skillInvocation')}>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs">{skillId}</span>
            <Link to={paths.skills()} className="text-xs text-brand-primary hover:underline">
              {t('detail.viewSkill')}
            </Link>
          </div>
        </Field>
      ) : null}

      {log.resourceType === 'agent_action' && log.resourceId ? (
        <Button variant="outline" size="sm" onClick={() => onViewChain(log.resourceType, log.resourceId!)}>
          {t('detail.viewChain')}
        </Button>
      ) : null}

      <Field label={t('detail.before')}>
        <Json value={log.before} />
      </Field>
      <Field label={t('detail.after')}>
        <Json value={log.after} />
      </Field>
      <Field label={t('detail.extra')}>
        <Json value={log.detail} />
      </Field>
    </div>
  )
}

export function AuditDetailSheet({
  log,
  open,
  onOpenChange,
  onViewChain,
}: {
  log: AuditLogOut | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onViewChain: (resourceType: string, resourceId: string) => void
}) {
  const { t } = useTranslation('audit')
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{t('detail.title')}</SheetTitle>
          <SheetDescription className="sr-only">{t('detail.title')}</SheetDescription>
        </SheetHeader>
        {log ? <Body log={log} onViewChain={onViewChain} /> : null}
      </SheetContent>
    </Sheet>
  )
}
