import type { IntakeOut } from '@worknexus/contracts'
import { Check, Clock, CopyX, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useIntakeQuery } from '@/features/intake/api/use-intake-query'
import { useUpdateIntakeMutation } from '@/features/intake/api/use-update-intake-mutation'
import { IntakeSourceBadge, IntakeStatusBadge } from '@/features/intake/components/intake-badges'
import { ConvertToWorkItemDialog } from '@/features/intake/components/convert-to-work-item-dialog'
import {
  MarkDuplicateDialog,
  RejectIntakeDialog,
  SnoozeIntakeDialog,
} from '@/features/intake/components/triage-action-dialogs'
import { TriageSuggestionCard } from '@/features/intake/components/triage-suggestion-card'
import { useHasPermission } from '@/lib/auth/use-has-permission'
import { formatDateTime } from '@/lib/datetime'
import { Markdown } from '@/lib/markdown'

const TERMINAL = new Set(['converted', 'rejected', 'duplicate'])

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="text-sm text-text-primary">{children}</dd>
    </div>
  )
}

function DrawerBody({ projectId, intake, onClose }: { projectId: string; intake: IntakeOut; onClose: () => void }) {
  const { t } = useTranslation(['common', 'intake'])
  const canTriage = useHasPermission('intake.triage', projectId)
  const updateMutation = useUpdateIntakeMutation(projectId)
  const [convertOpen, setConvertOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [snoozeOpen, setSnoozeOpen] = useState(false)
  const [duplicateOpen, setDuplicateOpen] = useState(false)

  const actionable = !TERMINAL.has(intake.status)

  return (
    <>
      <SheetHeader>
        <div className="flex flex-wrap items-center gap-2">
          <IntakeStatusBadge status={intake.status} />
          <IntakeSourceBadge source={intake.source} />
        </div>
        <SheetTitle>{intake.title}</SheetTitle>
      </SheetHeader>

      <div className="space-y-5">
        <TriageSuggestionCard intake={intake} canTriage={canTriage && actionable} onAdopt={() => setConvertOpen(true)} />

        {canTriage && actionable ? (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => setConvertOpen(true)}>
              <Check className="size-4" />
              {t('intake:actions.accept')}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setRejectOpen(true)}>
              <X className="size-4" />
              {t('intake:actions.reject')}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setDuplicateOpen(true)}>
              <CopyX className="size-4" />
              {t('intake:actions.markDuplicate')}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setSnoozeOpen(true)}>
              <Clock className="size-4" />
              {t('intake:actions.snooze')}
            </Button>
            {intake.status === 'new' ? (
              <Button
                size="sm"
                variant="ghost"
                disabled={updateMutation.isPending}
                onClick={() =>
                  updateMutation.mutate({ intakeId: intake.id, body: { status: 'triaging' } })
                }
              >
                {t('intake:actions.startTriage')}
              </Button>
            ) : null}
          </div>
        ) : null}

        <dl className="grid grid-cols-2 gap-4">
          <Field label={t('intake:detail.source')}>{t(`intake:source.${intake.source}`)}</Field>
          <Field label={t('intake:detail.createdAt')}>{formatDateTime(intake.createdAt)}</Field>
          {intake.snoozeUntil ? (
            <Field label={t('intake:detail.snoozedUntil')}>{formatDateTime(intake.snoozeUntil)}</Field>
          ) : null}
          {intake.rejectionReason ? (
            <Field label={t('intake:detail.rejectionReason')}>{intake.rejectionReason}</Field>
          ) : null}
        </dl>

        <div className="space-y-1">
          <p className="text-xs text-text-muted">{t('intake:detail.descriptionLabel')}</p>
          {intake.description ? (
            <Markdown content={intake.description} />
          ) : (
            <p className="text-sm text-text-muted">{t('intake:detail.noDescription')}</p>
          )}
        </div>

        {intake.convertedWorkItemId ? (
          <p className="text-sm text-text-secondary">
            {t('intake:detail.convertedTo')}: <span className="font-mono">{intake.convertedWorkItemId}</span>
          </p>
        ) : null}
        {intake.duplicateWorkItemId ? (
          <p className="text-sm text-text-secondary">
            {t('intake:detail.duplicateOf')}: <span className="font-mono">{intake.duplicateWorkItemId}</span>
          </p>
        ) : null}
      </div>

      <ConvertToWorkItemDialog
        open={convertOpen}
        onOpenChange={setConvertOpen}
        projectId={projectId}
        intake={intake}
        onConverted={onClose}
      />
      <RejectIntakeDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        projectId={projectId}
        intakeId={intake.id}
      />
      <SnoozeIntakeDialog
        open={snoozeOpen}
        onOpenChange={setSnoozeOpen}
        projectId={projectId}
        intakeId={intake.id}
      />
      <MarkDuplicateDialog
        open={duplicateOpen}
        onOpenChange={setDuplicateOpen}
        projectId={projectId}
        intakeId={intake.id}
      />
    </>
  )
}

function SheetLoader({ projectId, intakeId, onClose }: { projectId: string; intakeId: string; onClose: () => void }) {
  const { t } = useTranslation('intake')
  const query = useIntakeQuery(intakeId)
  if (query.isPending) {
    return (
      <>
        <SheetTitle className="sr-only">{t('title')}</SheetTitle>
        <PageSkeleton />
      </>
    )
  }
  if (query.isError) {
    return (
      <>
        <SheetTitle className="sr-only">{t('title')}</SheetTitle>
        <ErrorState onRetry={() => void query.refetch()} />
      </>
    )
  }
  return <DrawerBody projectId={projectId} intake={query.data} onClose={onClose} />
}

export function IntakeDetailSheet({
  projectId,
  intakeId,
  onClose,
}: {
  projectId: string
  intakeId: string | null
  onClose: () => void
}) {
  return (
    <Sheet
      open={intakeId !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent aria-describedby={undefined}>
        {intakeId !== null ? <SheetLoader projectId={projectId} intakeId={intakeId} onClose={onClose} /> : null}
      </SheetContent>
    </Sheet>
  )
}
