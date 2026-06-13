import { useDroppable } from '@dnd-kit/core'
import type { WorkItemOut, WorkItemStatus } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { BoardCard } from '@/features/work-items/components/board-card'
import { cn } from '@/lib/utils'

interface BoardColumnProps {
  status: WorkItemStatus
  items: WorkItemOut[]
  onSelect: (id: string) => void
}

export function BoardColumn({ status, items, onSelect }: BoardColumnProps) {
  const { t } = useTranslation('workItems')
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div className="flex w-64 shrink-0 flex-col rounded-lg bg-surface-secondary">
      <div className="flex items-center justify-between px-3 py-2 text-sm font-medium text-text-secondary">
        <span>{t(`status.${status}`)}</span>
        <span className="text-text-muted">{items.length}</span>
      </div>
      <div
        ref={setNodeRef}
        data-status={status}
        className={cn('flex min-h-24 flex-1 flex-col gap-2 p-2', isOver && 'ring-2 ring-inset ring-border-strong')}
      >
        {items.map((item) => (
          <BoardCard key={item.id} item={item} onSelect={onSelect} />
        ))}
      </div>
    </div>
  )
}
