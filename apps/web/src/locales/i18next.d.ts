import type auth from './zh-CN/auth'
import type common from './zh-CN/common'
import type projects from './zh-CN/projects'
import type settings from './zh-CN/settings'

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common'
    resources: {
      common: typeof common
      auth: typeof auth
      settings: typeof settings
      projects: typeof projects
    }
  }
}
