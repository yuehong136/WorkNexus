import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useCreateCommentMutation } from '@/features/work-items/api/use-create-comment-mutation'
import { useWorkItemCommentsQuery } from '@/features/work-items/api/use-work-item-comments-query'
import { formatDateTime } from '@/lib/datetime'
import { Markdown } from '@/lib/markdown'

export function WorkItemComments({ workItemId, canComment }: { workItemId: string; canComment: boolean }) {
  const { t } = useTranslation(['common', 'workItems'])
  const commentsQuery = useWorkItemCommentsQuery(workItemId)
  const mutation = useCreateCommentMutation(workItemId)
  const [body, setBody] = useState('')

  const submit = () => {
    const value = body.trim()
    if (!value) return
    mutation.mutate(
      { body: value },
      {
        onSuccess: () => {
          setBody('')
          toast.success(t('workItems:comments.added'))
        },
      },
    )
  }

  const comments = commentsQuery.data ?? []

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium text-text-secondary">{t('workItems:comments.title')}</h3>
      {comments.length > 0 ? (
        <ul className="space-y-3">
          {comments.map((comment) => (
            <li key={comment.id} className="rounded-md border border-border-default bg-surface-primary p-3">
              <div className="mb-1 flex items-center justify-between text-xs text-text-muted">
                <span>
                  {comment.author?.displayName ??
                    (comment.authorType === 'ai_agent'
                      ? t('workItems:comments.authorAi')
                      : t('workItems:comments.authorSystem'))}
                </span>
                <span>{formatDateTime(comment.createdAt)}</span>
              </div>
              <Markdown content={comment.body} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-text-muted">{t('workItems:comments.empty')}</p>
      )}
      {canComment ? (
        <div className="space-y-2">
          <Textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder={t('workItems:comments.placeholder')}
          />
          <div className="flex justify-end">
            <Button size="sm" disabled={mutation.isPending || !body.trim()} onClick={submit}>
              {t('workItems:comments.submit')}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
