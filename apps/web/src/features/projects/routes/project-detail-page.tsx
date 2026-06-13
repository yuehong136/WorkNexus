import { ListChecks, Pencil } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ProjectFormDialog } from '@/features/projects/components/project-form-dialog'
import { ProjectMembersSection } from '@/features/projects/components/project-members-section'
import { ProjectSummaryCards } from '@/features/projects/components/project-summary-cards'
import { useArchiveProjectMutation } from '@/features/projects/api/use-archive-project-mutation'
import { useProjectQuery } from '@/features/projects/api/use-project-query'
import { useHasPermission } from '@/lib/auth/use-has-permission'
import { formatDateTime } from '@/lib/datetime'
import { paths } from '@/lib/paths'

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="text-sm text-text-primary">{value}</dd>
    </div>
  )
}

export function ProjectDetailPage() {
  const { t } = useTranslation(['common', 'projects'])
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const [editOpen, setEditOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)

  const projectQuery = useProjectQuery(projectId)
  const archiveMutation = useArchiveProjectMutation()

  const canUpdate = useHasPermission('project.update', projectId)
  const canArchive = useHasPermission('project.archive', projectId)
  const canManageMembers = useHasPermission('project.member.manage', projectId)

  if (projectQuery.isPending) return <PageSkeleton />
  if (projectQuery.isError) return <ErrorState title={t('projects:detail.notFound')} />

  const project = projectQuery.data

  const confirmArchive = () => {
    archiveMutation.mutate(project.id, {
      onSuccess: () => {
        toast.success(t('projects:detail.archived'))
        setArchiveOpen(false)
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-text-primary">{project.name}</h1>
            <Badge variant={project.status === 'active' ? 'success' : 'secondary'}>
              {t(`projects:status.${project.status}`)}
            </Badge>
          </div>
          <p className="text-sm text-text-muted">{project.key}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void navigate(paths.workItems(project.id))}>
            <ListChecks className="size-4" />
            {t('projects:detail.workItems')}
          </Button>
          {canUpdate ? (
            <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
              <Pencil className="size-4" />
              {t('projects:detail.edit')}
            </Button>
          ) : null}
          {canArchive && project.status === 'active' ? (
            <Button variant="outline" size="sm" onClick={() => setArchiveOpen(true)}>
              {t('projects:detail.archive')}
            </Button>
          ) : null}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-4 rounded-lg border border-border-default bg-surface-primary p-4 sm:grid-cols-4">
        <Field label={t('projects:detail.owner')} value={project.owner?.displayName ?? t('projects:detail.noOwner')} />
        <Field label={t('projects:detail.memberCount')} value={project.memberCount} />
        <Field label={t('projects:detail.createdAt')} value={formatDateTime(project.createdAt)} />
        <Field label={t('projects:detail.key')} value={project.key} />
        <div className="col-span-2 space-y-1 sm:col-span-4">
          <dt className="text-xs text-text-muted">{t('projects:detail.descriptionLabel')}</dt>
          <dd className="text-sm text-text-primary">
            {project.description ? project.description : t('projects:detail.noDescription')}
          </dd>
        </div>
      </dl>

      <ProjectSummaryCards projectId={project.id} />

      <ProjectMembersSection projectId={project.id} ownerId={project.ownerId} canManage={canManageMembers} />

      <ProjectFormDialog open={editOpen} onOpenChange={setEditOpen} project={project} />
      <ConfirmDialog
        open={archiveOpen}
        onOpenChange={setArchiveOpen}
        title={t('projects:detail.archiveTitle')}
        description={t('projects:detail.archiveDescription', { name: project.name })}
        destructive
        loading={archiveMutation.isPending}
        onConfirm={confirmArchive}
      />
    </div>
  )
}
