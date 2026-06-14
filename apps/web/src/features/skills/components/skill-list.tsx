import type { SkillOut } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { cn } from '@/lib/utils'

import { RiskBadge } from './skill-badges'

export function SkillList({ skills }: { skills: SkillOut[] }) {
  const { t } = useTranslation('skills')
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {skills.map((skill) => (
        <div key={skill.skillCode} className="rounded-lg border border-border-default bg-surface-primary p-4">
          <h3 className="font-mono text-sm font-semibold text-text-primary">{skill.skillCode}</h3>
          <ul className="mt-3 space-y-2">
            {skill.tools.map((tool) => (
              <li key={tool.toolName} className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-text-secondary">{tool.toolName}</span>
                <div className="flex items-center gap-2">
                  <RiskBadge risk={tool.riskLevel} />
                  <span
                    className={cn(
                      'text-xs',
                      tool.executableInV01 ? 'text-status-success' : 'text-text-muted',
                    )}
                  >
                    {tool.executableInV01 ? t('executable.yes') : t('executable.no')}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}
