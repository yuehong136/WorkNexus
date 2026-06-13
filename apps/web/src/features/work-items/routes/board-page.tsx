import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { useWorkItemsQuery } from '@/features/work-items/api/use-work-items-query'
import { Board } from '@/features/work-items/components/board'
import { WorkItemDrawer } from '@/features/work-items/components/work-item-drawer'
import { useHasPermission } from '@/lib/auth/use-has-permission'
import { paths } from '@/lib/paths'

export function BoardPage() {
  const { t } = useTranslation('workItems')
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const query = useWorkItemsQuery(projectId, { page: 1, page_size: 100 })
  const canTransition = useHasPermission('work_item.transition', projectId)

  return (
    <div className="space-y-6">
      <Link to={paths.projectDetail(projectId)} className="text-sm text-text-muted hover:underline">
        ← {t('backToProject')}
      </Link>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">{t('board.title')}</h1>
        <Button variant="outline" size="sm" onClick={() => void navigate(paths.workItems(projectId))}>
          {t('board.listView')}
        </Button>
      </div>
      {query.isPending ? (
        <PageSkeleton />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : (
        <Board
          projectId={projectId}
          items={query.data.items}
          onSelect={setSelectedId}
          canTransition={canTransition}
        />
      )}
      <WorkItemDrawer projectId={projectId} workItemId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
