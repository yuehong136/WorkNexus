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
import { Textarea } from '@/components/ui/textarea'
import { intakeErrorMessage } from '@/features/intake/api/error-messages'
import { intakeCreateSchema, type IntakeCreateValues } from '@/features/intake/api/schemas'
import { useCreateIntakeMutation } from '@/features/intake/api/use-create-intake-mutation'

interface IntakeFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
}

export function IntakeFormDialog({ open, onOpenChange, projectId }: IntakeFormDialogProps) {
  const { t } = useTranslation(['common', 'intake'])
  const mutation = useCreateIntakeMutation(projectId)

  const form = useForm<IntakeCreateValues>({
    resolver: zodResolver(intakeCreateSchema(t)),
    defaultValues: { title: '', description: '' },
  })

  const errorMessage = intakeErrorMessage(mutation.error, t)

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
        title: values.title,
        description: values.description?.trim() ? values.description.trim() : null,
      },
      {
        onSuccess: () => {
          toast.success(t('intake:create.success'))
          close(false)
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('intake:create.title')}</DialogTitle>
          <DialogDescription>{t('intake:create.description')}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('intake:form.title')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('intake:form.titlePlaceholder')} {...field} />
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
                  <FormLabel>{t('intake:form.description')}</FormLabel>
                  <FormControl>
                    <Textarea placeholder={t('intake:form.descriptionPlaceholder')} rows={4} {...field} />
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
                {t('intake:create.submit')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
