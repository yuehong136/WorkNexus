import { useTranslation } from 'react-i18next'

import { Markdown } from '@/lib/markdown'
import { cn } from '@/lib/utils'

interface MessageBubbleProps {
  role: 'user' | 'ai' | 'system'
  content: string
  pending?: boolean
}

export function MessageBubble({ role, content, pending = false }: MessageBubbleProps) {
  const { t } = useTranslation('workchat')
  const isUser = role === 'user'
  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-3 py-2',
          isUser ? 'bg-brand-primary text-brand-primary-foreground' : 'bg-surface-secondary text-text-primary',
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
        ) : content ? (
          <Markdown content={content} />
        ) : pending ? (
          <p className="text-sm text-text-muted">{t('thinking')}</p>
        ) : null}
      </div>
    </div>
  )
}
