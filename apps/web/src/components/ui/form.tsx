import { Label as LabelPrimitive, Slot } from 'radix-ui'
import { createContext, useContext, useId, type ComponentProps } from 'react'
import {
  Controller,
  FormProvider,
  useFormContext,
  useFormState,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
} from 'react-hook-form'

import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

export const Form = FormProvider

interface FormFieldContextValue {
  name: string
}

const FormFieldContext = createContext<FormFieldContextValue | null>(null)

interface FormItemContextValue {
  id: string
}

const FormItemContext = createContext<FormItemContextValue | null>(null)

export function FormField<TFieldValues extends FieldValues, TName extends FieldPath<TFieldValues>>(
  props: ControllerProps<TFieldValues, TName>,
) {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  )
}

function useFormField() {
  const fieldContext = useContext(FormFieldContext)
  const itemContext = useContext(FormItemContext)
  const { getFieldState } = useFormContext()
  const formState = useFormState()
  if (!fieldContext || !itemContext) {
    throw new Error('useFormField must be used within <FormField> and <FormItem>')
  }
  const fieldState = getFieldState(fieldContext.name, formState)
  const { id } = itemContext
  return {
    id,
    name: fieldContext.name,
    formItemId: `${id}-form-item`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  }
}

export function FormItem({ className, ...props }: ComponentProps<'div'>) {
  const id = useId()
  return (
    <FormItemContext.Provider value={{ id }}>
      <div className={cn('grid gap-2', className)} {...props} />
    </FormItemContext.Provider>
  )
}

export function FormLabel({ className, ...props }: ComponentProps<typeof LabelPrimitive.Root>) {
  const { error, formItemId } = useFormField()
  return <Label className={cn(error && 'text-status-error', className)} htmlFor={formItemId} {...props} />
}

export function FormControl(props: ComponentProps<typeof Slot.Root>) {
  const { error, formItemId, formMessageId } = useFormField()
  return (
    <Slot.Root
      id={formItemId}
      aria-describedby={error ? formMessageId : undefined}
      aria-invalid={!!error}
      {...props}
    />
  )
}

export function FormMessage({ className, ...props }: ComponentProps<'p'>) {
  const { error, formMessageId } = useFormField()
  const body = error ? String(error.message ?? '') : props.children
  if (!body) return null
  return (
    <p id={formMessageId} className={cn('text-sm text-status-error', className)} {...props}>
      {body}
    </p>
  )
}
