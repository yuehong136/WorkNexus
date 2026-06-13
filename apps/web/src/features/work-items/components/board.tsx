import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import type { WorkItemOut, WorkItemStatus } from '@worknexus/contracts'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { workItemErrorMessage } from '@/features/work-items/api/error-messages'
import { WORK_ITEM_STATUSES } from '@/features/work-items/api/schemas'
import { useBoardTransitionMutation } from '@/features/work-items/api/use-board-transition-mutation'
import { BoardCard } from '@/features/work-items/components/board-card'
import { BoardColumn } from '@/features/work-items/components/board-column'

interface BoardProps {
  projectId: string
  items: WorkItemOut[]
  onSelect: (id: string) => void
  canTransition: boolean
}

export function Board({ projectId, items, onSelect, canTransition }: BoardProps) {
  const { t } = useTranslation(['common', 'workItems'])
  const transition = useBoardTransitionMutation(projectId)
  const [activeId, setActiveId] = useState<string | null>(null)
  const pointerSensor = useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  const sensors = useSensors(...(canTransition ? [pointerSensor] : []))

  const activeItem = items.find((item) => item.id === activeId) ?? null

  const onDragEnd = (event: DragEndEvent) => {
    setActiveId(null)
    const { active, over } = event
    if (!over) return
    const item = items.find((candidate) => candidate.id === active.id)
    const target = over.id as WorkItemStatus
    if (!item || item.status === target) return
    transition.mutate(
      { workItemId: item.id, status: target },
      {
        onError: (error) => {
          const message = workItemErrorMessage(error, t)
          if (message) toast.error(message)
        },
      },
    )
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(event: DragStartEvent) => setActiveId(event.active.id as string)}
      onDragEnd={onDragEnd}
    >
      <div className="flex gap-3 overflow-x-auto pb-2">
        {WORK_ITEM_STATUSES.map((status) => (
          <BoardColumn
            key={status}
            status={status}
            items={items.filter((item) => item.status === status)}
            onSelect={onSelect}
          />
        ))}
      </div>
      <DragOverlay>{activeItem ? <BoardCard item={activeItem} overlay /> : null}</DragOverlay>
    </DndContext>
  )
}
