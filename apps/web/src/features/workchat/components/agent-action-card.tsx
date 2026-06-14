import type { AgentActionOut } from '@worknexus/contracts'
import { Bot, Check, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { useApproveAgentActionMutation } from '@/features/workchat/api/use-approve-agent-action-mutation'
import { useRejectAgentActionMutation } from '@/features/workchat/api/use-reject-agent-action-mutation'
import { AgentActionStatusBadge } from '@/features/workchat/components/agent-action-status-badge'

/**
 * The confirmation surface for an AI-proposed write. The card itself is the confirm step
 * (no nested ConfirmDialog): Approve runs the backend double-check + executes; Reject
 * records the decision. Pending actions show the action buttons; resolved ones show status.
 */
export function AgentActionCard({ action }: { action: AgentActionOut }) {
  const { t } = useTranslation('workchat')
  const approve = useApproveAgentActionMutation()
  const reject = useRejectAgentActionMutation()
  const busy = approve.isPending || reject.isPending
  const isPending = action.status === 'pending'

  return (
    <div className="rounded-lg border border-border-default bg-surface-primary p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Bot className="size-4 text-brand-primary" />
          {t(`actionType.${action.actionType}`)}
        </div>
        <AgentActionStatusBadge status={action.status} />
      </div>

      <dl className="space-y-1 rounded-md bg-surface-secondary p-2 text-xs">
        {Object.entries(action.arguments).map(([key, value]) => (
          <div key={key} className="flex gap-2">
            <dt className="shrink-0 text-text-muted">{key}</dt>
            <dd className="break-all text-text-secondary">{formatValue(value)}</dd>
          </div>
        ))}
      </dl>

      {action.errorMessage ? <p className="mt-2 text-xs text-status-error">{action.errorMessage}</p> : null}

      {isPending ? (
        <div className="mt-3 flex gap-2">
          <Button size="sm" disabled={busy} onClick={() => approve.mutate(action.id)}>
            <Check className="size-4" />
            {t('actions.approve')}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => reject.mutate({ agentActionId: action.id })}
          >
            <X className="size-4" />
            {t('actions.reject')}
          </Button>
        </div>
      ) : null}
    </div>
  )
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}
