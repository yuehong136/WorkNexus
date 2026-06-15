import type auth from './zh-CN/auth'
import type common from './zh-CN/common'
import type intake from './zh-CN/intake'
import type projects from './zh-CN/projects'
import type settings from './zh-CN/settings'
import type skills from './zh-CN/skills'
import type workchat from './zh-CN/workchat'
import type workItems from './zh-CN/workItems'

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common'
    resources: {
      common: typeof common
      auth: typeof auth
      settings: typeof settings
      projects: typeof projects
      workItems: typeof workItems
      intake: typeof intake
      skills: typeof skills
      workchat: typeof workchat
    }
  }
}
