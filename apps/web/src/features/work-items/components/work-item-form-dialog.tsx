import { zodResolver } from '@hookform/resolvers/zod'
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
import { workItemErrorMessage } from '@/features/work-items/api/error-messages'
import {
  WORK_ITEM_PRIORITIES,
  WORK_ITEM_TYPES,
  workItemCreateSchema,
  type WorkItemCreateValues,
} from '@/features/work-items/api/schemas'
import { useCreateWorkItemMutation } from '@/features/work-items/api/use-create-work-item-mutation'
import { cn } from '@/lib/utils'

const selectClassName =
  'flex h-9 w-full rounded-md border border-border-default bg-surface-primary px-3 py-1 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

interface WorkItemFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
}

export function WorkItemFormDialog({ open, onOpenChange, projectId }: WorkItemFormDialogProps) {
  const { t } = useTranslation(['common', 'workItems'])
  const mutation = useCreateWorkItemMutation(projectId)

  const form = useForm<WorkItemCreateValues>({
    resolver: zodResolver(workItemCreateSchema(t)),
    defaultValues: { type: 'task', title: '', description: '', priority: 'medium' },
  })

  const errorMessage = workItemErrorMessage(mutation.error, t)

  const close = (next: boolean) => {
    if (!next) {
      form.reset()
      mutation.reset()
    }
    onOpenChange(next)
  }

  const onSubmit = form.handleSubmit((values) => {
    mutation.mutate(
      {
        type: values.type,
        title: values.title,
        priority: values.priority,
        description: values.description?.trim() ? values.description.trim() : null,
      },
      {
        onSuccess: () => {
          toast.success(t('workItems:create.success'))
          close(false)
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('workItems:create.title')}</DialogTitle>
          <DialogDescription>{t('workItems:create.description')}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('workItems:form.type')}</FormLabel>
                  <FormControl>
                    <select className={cn(selectClassName)} {...field}>
                      {WORK_ITEM_TYPES.map((type) => (
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
                  <FormLabel>{t('workItems:form.title')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('workItems:form.titlePlaceholder')} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('workItems:form.description')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('workItems:form.descriptionPlaceholder')} {...field} />
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
                  <FormLabel>{t('workItems:form.priority')}</FormLabel>
                  <FormControl>
                    <select className={cn(selectClassName)} {...field}>
                      {WORK_ITEM_PRIORITIES.map((priority) => (
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
            {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => close(false)}>
                {t('actions.cancel')}
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {t('workItems:create.submit')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
