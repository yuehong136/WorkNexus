import { useDraggable } from '@dnd-kit/core'
import type { WorkItemOut } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { PriorityBadge, SourceBadge, TypeBadge } from '@/features/work-items/components/work-item-badges'
import { cn } from '@/lib/utils'

interface BoardCardProps {
  item: WorkItemOut
  onSelect?: (id: string) => void
  overlay?: boolean
}

export function BoardCard({ item, onSelect, overlay = false }: BoardCardProps) {
  const { t } = useTranslation('workItems')
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: item.id })
  const dragProps = overlay ? {} : { ref: setNodeRef, ...attributes, ...listeners }
  const style = !overlay && transform ? { transform: `translate(${transform.x}px, ${transform.y}px)` } : undefined
  const aiSource = item.source === 'ai_chat' || item.source === 'mcp'

  return (
    <div
      {...dragProps}
      style={style}
      onClick={() => onSelect?.(item.id)}
      className={cn(
        'cursor-grab rounded-md border border-border-default bg-surface-primary p-3 shadow-sm',
        !overlay && isDragging && 'opacity-40',
        overlay && 'cursor-grabbing shadow-lg',
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="font-mono text-xs text-text-secondary">{item.key}</span>
        <TypeBadge type={item.type} />
      </div>
      <p className="mb-2 line-clamp-2 text-sm font-medium text-text-primary">{item.title}</p>
      <div className="flex flex-wrap items-center gap-2">
        <PriorityBadge priority={item.priority} />
        {aiSource ? <SourceBadge source={item.source} /> : null}
        <span className="ml-auto text-xs text-text-muted">{item.assignee?.displayName ?? t('noAssignee')}</span>
      </div>
    </div>
  )
}
