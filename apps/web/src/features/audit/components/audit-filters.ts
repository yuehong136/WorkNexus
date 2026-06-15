import type { AuditActorType } from '@worknexus/contracts'

export interface AuditFilters {
  actorType: AuditActorType | ''
  action: string
  resourceType: string
  resourceId: string // set only by "view chain"; not rendered as a control
  projectId: string
  fromDate: string
  toDate: string
}

export const emptyAuditFilters: AuditFilters = {
  actorType: '',
  action: '',
  resourceType: '',
  resourceId: '',
  projectId: '',
  fromDate: '',
  toDate: '',
}
