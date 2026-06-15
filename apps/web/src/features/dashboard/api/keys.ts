import type { GetDashboardOverdueParams } from '@worknexus/contracts'

export const dashboardKeys = {
  all: ['dashboard'] as const,
  project: (projectId: string) => [...dashboardKeys.all, projectId] as const,
  summary: (projectId: string) => [...dashboardKeys.project(projectId), 'summary'] as const,
  workload: (projectId: string) => [...dashboardKeys.project(projectId), 'workload'] as const,
  overdue: (projectId: string, params: GetDashboardOverdueParams) =>
    [...dashboardKeys.project(projectId), 'overdue', params] as const,
  insights: (projectId: string) => [...dashboardKeys.project(projectId), 'insights'] as const,
}
