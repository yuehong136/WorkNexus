import { zodResolver } from '@hookform/resolvers/zod'
import type { ProjectOut } from '@worknexus/contracts'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
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
import { projectErrorMessage } from '@/features/projects/api/error-messages'
import { projectCreateSchema, type ProjectCreateValues } from '@/features/projects/api/schemas'
import { useCreateProjectMutation } from '@/features/projects/api/use-create-project-mutation'
import { useUpdateProjectMutation } from '@/features/projects/api/use-update-project-mutation'
import { paths } from '@/lib/paths'

interface ProjectFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project?: ProjectOut
}

export function ProjectFormDialog({ open, onOpenChange, project }: ProjectFormDialogProps) {
  const { t } = useTranslation(['common', 'projects'])
  const navigate = useNavigate()
  const editing = project !== undefined
  const schema = useMemo(() => projectCreateSchema(t), [t])
  const createMutation = useCreateProjectMutation()
  const updateMutation = useUpdateProjectMutation()
  const mutation = editing ? updateMutation : createMutation

  const form = useForm<ProjectCreateValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: project?.name ?? '',
      key: project?.key ?? '',
      description: project?.description ?? '',
    },
  })

  const errorMessage = projectErrorMessage(mutation.error, t)

  const close = (next: boolean) => {
    if (!next) {
      form.reset()
      createMutation.reset()
      updateMutation.reset()
    }
    onOpenChange(next)
  }

  const onSubmit = form.handleSubmit((values) => {
    const description = values.description?.trim() ? values.description.trim() : null
    if (editing) {
      updateMutation.mutate(
        { projectId: project.id, body: { name: values.name, description } },
        {
          onSuccess: () => {
            toast.success(t('projects:edit.success'))
            close(false)
          },
        },
      )
    } else {
      createMutation.mutate(
        { name: values.name, key: values.key, description },
        {
          onSuccess: (created) => {
            toast.success(t('projects:create.success'))
            close(false)
            void navigate(paths.projectDetail(created.id))
          },
        },
      )
    }
  })

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? t('projects:edit.title') : t('projects:create.title')}</DialogTitle>
          <DialogDescription>
            {editing ? t('projects:edit.description') : t('projects:create.description')}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('projects:form.name')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('projects:form.namePlaceholder')} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('projects:form.key')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('projects:form.keyPlaceholder')} disabled={editing} {...field} />
                  </FormControl>
                  <p className="text-xs text-text-muted">{t('projects:form.keyHint')}</p>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('projects:form.description')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('projects:form.descriptionPlaceholder')} {...field} />
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
                {editing ? t('projects:edit.submit') : t('projects:create.submit')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
