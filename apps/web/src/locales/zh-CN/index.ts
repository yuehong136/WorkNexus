import audit from './audit'
import auth from './auth'
import common from './common'
import dashboard from './dashboard'
import intake from './intake'
import projects from './projects'
import settings from './settings'
import skills from './skills'
import workchat from './workchat'
import workItems from './workItems'

export default { common, auth, settings, projects, workItems, intake, dashboard, skills, workchat, audit } as const
