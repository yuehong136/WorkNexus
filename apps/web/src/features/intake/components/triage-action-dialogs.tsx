import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { intakeErrorMessage } from '@/features/intake/api/error-messages'
import { useConvertCandidatesQuery } from '@/features/intake/api/use-convert-candidates-query'
import { useMarkDuplicateMutation } from '@/features/intake/api/use-mark-duplicate-mutation'
import { useRejectIntakeMutation } from '@/features/intake/api/use-reject-intake-mutation'
import { useSnoozeIntakeMutation } from '@/features/intake/api/use-snooze-intake-mutation'

const fieldClassName =
  'flex h-9 w-full rounded-md border border-border-default bg-surface-primary px-3 py-1 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

interface ActionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  intakeId: string
  onDone?: () => void
}

export function RejectIntakeDialog({ open, onOpenChange, projectId, intakeId, onDone }: ActionDialogProps) {
  const { t } = useTranslation(['common', 'intake'])
  const mutation = useRejectIntakeMutation(projectId)
  const [reason, setReason] = useState('')

  // Reset on close (event handler, not an effect) so the next open starts clean.
  const close = (next: boolean) => {
    if (!next) {
      setReason('')
      mutation.reset()
    }
    onOpenChange(next)
  }

  const errorMessage = intakeErrorMessage(mutation.error, t)

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('intake:reject.title')}</DialogTitle>
          <DialogDescription>{t('intake:reject.description')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label className="text-sm text-text-secondary" htmlFor="reject-reason">
            {t('intake:reject.reason')}
          </label>
          <Textarea
            id="reject-reason"
            rows={3}
            placeholder={t('intake:reject.reasonPlaceholder')}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>
        {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => close(false)}>
            {t('actions.cancel')}
          </Button>
          <Button
            variant="destructive"
            disabled={mutation.isPending}
            onClick={() =>
              mutation.mutate(
                { intakeId, body: { reason: reason.trim() ? reason.trim() : null } },
                {
                  onSuccess: () => {
                    toast.success(t('intake:reject.success'))
                    close(false)
                    onDone?.()
                  },
                },
              )
            }
          >
            {t('intake:reject.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function SnoozeIntakeDialog({ open, onOpenChange, projectId, intakeId, onDone }: ActionDialogProps) {
  const { t } = useTranslation(['common', 'intake'])
  const mutation = useSnoozeIntakeMutation(projectId)
  const [value, setValue] = useState('')

  const close = (next: boolean) => {
    if (!next) {
      setValue('')
      mutation.reset()
    }
    onOpenChange(next)
  }

  const errorMessage = intakeErrorMessage(mutation.error, t)

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('intake:snooze.title')}</DialogTitle>
          <DialogDescription>{t('intake:snooze.description')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label className="text-sm text-text-secondary" htmlFor="snooze-until">
            {t('intake:snooze.until')}
          </label>
          <input
            id="snooze-until"
            type="datetime-local"
            className={fieldClassName}
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        </div>
        {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => close(false)}>
            {t('actions.cancel')}
          </Button>
          <Button
            disabled={mutation.isPending || !value}
            onClick={() =>
              mutation.mutate(
                { intakeId, body: { snoozeUntil: new Date(value).toISOString() } },
                {
                  onSuccess: () => {
                    toast.success(t('intake:snooze.success'))
                    close(false)
                    onDone?.()
                  },
                },
              )
            }
          >
            {t('intake:snooze.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function MarkDuplicateDialog({ open, onOpenChange, projectId, intakeId, onDone }: ActionDialogProps) {
  const { t } = useTranslation(['common', 'intake'])
  const mutation = useMarkDuplicateMutation(projectId)
  const candidates = useConvertCandidatesQuery(projectId, { enabled: open })
  const [target, setTarget] = useState('')

  const close = (next: boolean) => {
    if (!next) {
      setTarget('')
      mutation.reset()
    }
    onOpenChange(next)
  }

  const errorMessage = intakeErrorMessage(mutation.error, t)
  const items = candidates.data?.items ?? []

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('intake:duplicate.title')}</DialogTitle>
          <DialogDescription>{t('intake:duplicate.description')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label className="text-sm text-text-secondary" htmlFor="duplicate-target">
            {t('intake:duplicate.target')}
          </label>
          {items.length === 0 ? (
            <p className="text-sm text-text-muted">{t('intake:duplicate.noWorkItems')}</p>
          ) : (
            <select
              id="duplicate-target"
              className={fieldClassName}
              value={target}
              onChange={(event) => setTarget(event.target.value)}
            >
              <option value="">{t('intake:duplicate.targetPlaceholder')}</option>
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.key} · {item.title}
                </option>
              ))}
            </select>
          )}
        </div>
        {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => close(false)}>
            {t('actions.cancel')}
          </Button>
          <Button
            disabled={mutation.isPending || !target}
            onClick={() =>
              mutation.mutate(
                { intakeId, body: { duplicateWorkItemId: target } },
                {
                  onSuccess: () => {
                    toast.success(t('intake:duplicate.success'))
                    close(false)
                    onDone?.()
                  },
                },
              )
            }
          >
            {t('intake:duplicate.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
