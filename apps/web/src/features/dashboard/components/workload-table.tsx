import type { WorkloadItemOut } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { workloadColumns } from '@/features/dashboard/components/workload-columns'

export function WorkloadTable({ items }: { items: WorkloadItemOut[] }) {
  const { t } = useTranslation(['common', 'dashboard', 'workItems'])
  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium text-text-secondary">{t('dashboard:workload.title')}</h3>
      <DataTable
        columns={workloadColumns(t)}
        data={items}
        emptyState={<EmptyState description={t('dashboard:workload.empty')} />}
      />
    </section>
  )
}
