import { zodResolver } from '@hookform/resolvers/zod'
import type { ProjectMemberOut, WorkItemOut } from '@worknexus/contracts'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { workItemErrorMessage } from '@/features/work-items/api/error-messages'
import {
  CUSTOM_FIELDS_BY_TYPE,
  WORK_ITEM_PRIORITIES,
  workItemEditSchema,
  type WorkItemEditValues,
} from '@/features/work-items/api/schemas'
import { useUpdateWorkItemMutation } from '@/features/work-items/api/use-update-work-item-mutation'
import { cn } from '@/lib/utils'

const selectClassName =
  'flex h-9 w-full rounded-md border border-border-default bg-surface-primary px-3 py-1 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

interface WorkItemEditFormProps {
  projectId: string
  item: WorkItemOut
  members: ProjectMemberOut[]
  onDone: () => void
}

export function WorkItemEditForm({ projectId, item, members, onDone }: WorkItemEditFormProps) {
  const { t } = useTranslation(['common', 'workItems'])
  const mutation = useUpdateWorkItemMutation(projectId, item.id)
  const customKeys = CUSTOM_FIELDS_BY_TYPE[item.type]

  const [custom, setCustom] = useState<Record<string, string>>(() => {
    const source = (item.customFields ?? {}) as Record<string, unknown>
    const initial: Record<string, string> = {}
    for (const key of customKeys) {
      const value = source[key]
      initial[key] = Array.isArray(value) ? value.join(', ') : value == null ? '' : String(value)
    }
    return initial
  })

  const assigneeOptions = members.map((member) => ({ id: member.userId, label: member.displayName }))
  if (item.assigneeId && !members.some((member) => member.userId === item.assigneeId)) {
    assigneeOptions.unshift({ id: item.assigneeId, label: item.assignee?.displayName ?? item.assigneeId })
  }

  const form = useForm<WorkItemEditValues>({
    resolver: zodResolver(workItemEditSchema(t)),
    defaultValues: {
      title: item.title,
      description: item.description ?? '',
      priority: item.priority,
      assigneeId: item.assigneeId ?? '',
      acceptanceCriteria: item.acceptanceCriteria ?? '',
    },
  })

  const errorMessage = workItemErrorMessage(mutation.error, t)

  const onSubmit = form.handleSubmit((values) => {
    const customFields: Record<string, unknown> = {}
    for (const key of customKeys) {
      const raw = custom[key]?.trim()
      if (!raw) continue
      customFields[key] = key === 'approvers' ? raw.split(',').map((s) => s.trim()).filter(Boolean) : raw
    }
    mutation.mutate(
      {
        title: values.title,
        description: values.description?.trim() ? values.description.trim() : null,
        priority: values.priority,
        assigneeId: values.assigneeId ? values.assigneeId : null,
        acceptanceCriteria: values.acceptanceCriteria?.trim() ? values.acceptanceCriteria.trim() : null,
        customFields,
      },
      {
        onSuccess: () => {
          toast.success(t('workItems:edit.success'))
          onDone()
        },
      },
    )
  })

  return (
    <Form {...form}>
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('workItems:form.title')}</FormLabel>
              <FormControl>
                <Input {...field} />
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
                <Textarea placeholder={t('workItems:form.descriptionPlaceholder')} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="priority"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('workItems:form.priority')}</FormLabel>
                <FormControl>
                  <select className={cn(selectClassName)} {...field}>
                    {WORK_ITEM_PRIORITIES.map((value) => (
                      <option key={value} value={value}>
                        {t(`workItems:priority.${value}`)}
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
                <FormLabel>{t('workItems:form.assignee')}</FormLabel>
                <FormControl>
                  <select className={cn(selectClassName)} {...field}>
                    <option value="">{t('workItems:form.assigneeUnset')}</option>
                    {assigneeOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="acceptanceCriteria"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('workItems:form.acceptanceCriteria')}</FormLabel>
              <FormControl>
                <Textarea placeholder={t('workItems:form.acceptanceCriteriaPlaceholder')} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {customKeys.length > 0 ? (
          <div className="space-y-3">
            <p className="text-xs font-medium text-text-secondary">{t('workItems:form.customFields')}</p>
            {customKeys.map((key) => (
              <div key={key} className="space-y-1">
                <label className="text-sm text-text-secondary">{t(`workItems:customFields.${key}`)}</label>
                <Input
                  value={custom[key] ?? ''}
                  onChange={(event) => setCustom((prev) => ({ ...prev, [key]: event.target.value }))}
                />
              </div>
            ))}
          </div>
        ) : null}
        {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onDone}>
            {t('workItems:edit.cancel')}
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {t('workItems:edit.save')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
