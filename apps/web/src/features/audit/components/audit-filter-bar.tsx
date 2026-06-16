import { AuditAction, AuditActorType } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { type AuditFilters, emptyAuditFilters } from '@/features/audit/components/audit-filters'
import { useMeQuery } from '@/lib/auth/use-me-query'

const ACTOR_TYPES = Object.values(AuditActorType)
const ACTIONS = Object.values(AuditAction)
// Curated resource types that actually appear in audit rows (rendered as stable codes).
const RESOURCE_TYPES = [
  'work_item',
  'agent_action',
  'skill_invocation',
  'intake_request',
  'project',
  'user',
  'session',
  'invite',
  'role_binding',
  'tenant',
]

const controlClassName =
  'h-9 rounded-md border border-border-default bg-surface-primary px-3 text-sm text-text-primary'

export function AuditFilterBar({
  filters,
  onChange,
}: {
  filters: AuditFilters
  onChange: (next: AuditFilters) => void
}) {
  const { t } = useTranslation('audit')
  const { data: me } = useMeQuery()
  const projects = me?.projects ?? []
  const set = (patch: Partial<AuditFilters>) => onChange({ ...filters, ...patch })

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        className={controlClassName}
        value={filters.actorType}
        onChange={(e) => set({ actorType: e.target.value as AuditActorType | '' })}
      >
        <option value="">{t('filters.allActorTypes')}</option>
        {ACTOR_TYPES.map((a) => (
          <option key={a} value={a}>
            {t(`actorType.${a}`)}
          </option>
        ))}
      </select>
      <select className={controlClassName} value={filters.action} onChange={(e) => set({ action: e.target.value })}>
        <option value="">{t('filters.allActions')}</option>
        {ACTIONS.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
      <select
        className={controlClassName}
        value={filters.resourceType}
        onChange={(e) => set({ resourceType: e.target.value, resourceId: '' })}
      >
        <option value="">{t('filters.allResourceTypes')}</option>
        {RESOURCE_TYPES.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      <select className={controlClassName} value={filters.projectId} onChange={(e) => set({ projectId: e.target.value })}>
        <option value="">{t('filters.allProjects')}</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <input
        type="date"
        className={controlClassName}
        aria-label={t('filters.from')}
        value={filters.fromDate}
        onChange={(e) => set({ fromDate: e.target.value })}
      />
      <input
        type="date"
        className={controlClassName}
        aria-label={t('filters.to')}
        value={filters.toDate}
        onChange={(e) => set({ toDate: e.target.value })}
      />
      <Button variant="ghost" size="sm" onClick={() => onChange(emptyAuditFilters)}>
        {t('filters.reset')}
      </Button>
    </div>
  )
}
