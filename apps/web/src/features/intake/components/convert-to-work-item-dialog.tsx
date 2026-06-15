import { zodResolver } from '@hookform/resolvers/zod'
import type { IntakeOut } from '@worknexus/contracts'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
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
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { intakeErrorMessage } from '@/features/intake/api/error-messages'
import {
  CONVERT_PRIORITIES,
  CONVERT_TYPES,
  intakeConvertSchema,
  type IntakeConvertValues,
} from '@/features/intake/api/schemas'
import { useAcceptIntakeMutation } from '@/features/intake/api/use-accept-intake-mutation'
import { useProjectMembersQuery } from '@/features/intake/api/use-project-members-query'
import { cn } from '@/lib/utils'

const selectClassName =
  'flex h-9 w-full rounded-md border border-border-default bg-surface-primary px-3 py-1 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

interface ConvertToWorkItemDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  intake: IntakeOut
  onConverted?: () => void
}

export function ConvertToWorkItemDialog({
  open,
  onOpenChange,
  projectId,
  intake,
  onConverted,
}: ConvertToWorkItemDialogProps) {
  const { t } = useTranslation(['common', 'intake', 'workItems'])
  const mutation = useAcceptIntakeMutation(projectId)
  const membersQuery = useProjectMembersQuery(projectId, { enabled: open })

  const form = useForm<IntakeConvertValues>({
    resolver: zodResolver(intakeConvertSchema(t)),
    defaultValues: {
      type: intake.suggestedType ?? 'task',
      title: intake.title,
      priority: intake.suggestedPriority ?? 'medium',
      assigneeId: intake.suggestedAssigneeId ?? '',
    },
  })

  // Re-seed from the suggestions whenever a different intake's dialog opens.
  useEffect(() => {
    if (open) {
      form.reset({
        type: intake.suggestedType ?? 'task',
        title: intake.title,
        priority: intake.suggestedPriority ?? 'medium',
        assigneeId: intake.suggestedAssigneeId ?? '',
      })
      mutation.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, intake.id])

  const errorMessage = intakeErrorMessage(mutation.error, t)

  const onSubmit = form.handleSubmit((values) => {
    mutation.mutate(
      {
        intakeId: intake.id,
        body: {
          type: values.type,
          title: values.title,
          priority: values.priority,
          assigneeId: values.assigneeId || null,
        },
      },
      {
        onSuccess: () => {
          toast.success(t('intake:accept.success'))
          onOpenChange(false)
          onConverted?.()
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('intake:accept.title')}</DialogTitle>
          <DialogDescription>{t('intake:accept.description')}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('intake:accept.typeLabel')}</FormLabel>
                  <FormControl>
                    <select className={cn(selectClassName)} {...field}>
                      {CONVERT_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {t(`workItems:type.${type}`)}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('intake:accept.titleLabel')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="priority"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('intake:accept.priorityLabel')}</FormLabel>
                  <FormControl>
                    <select className={cn(selectClassName)} {...field}>
                      {CONVERT_PRIORITIES.map((priority) => (
                        <option key={priority} value={priority}>
                          {t(`workItems:priority.${priority}`)}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="assigneeId"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('intake:accept.assigneeLabel')}</FormLabel>
                  <FormControl>
                    <select className={cn(selectClassName)} {...field}>
                      <option value="">{t('intake:accept.assigneeUnset')}</option>
                      {(membersQuery.data ?? []).map((member) => (
                        <option key={member.userId} value={member.userId}>
                          {member.displayName}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t('actions.cancel')}
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {t('intake:accept.submit')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
