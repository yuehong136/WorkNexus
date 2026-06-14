import { BookOpen } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export function KnowledgeReferenceCard({ references }: { references: Array<Record<string, unknown>> }) {
  const { t } = useTranslation('workchat')
  if (references.length === 0) return null
  return (
    <div className="rounded-lg border border-border-default bg-surface-primary p-3">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-text-primary">
        <BookOpen className="size-4 text-text-muted" />
        {t('knowledge.title')}
      </div>
      <ul className="space-y-1 text-xs text-text-secondary">
        {references.map((reference, index) => (
          <li key={index} className="break-all">
            {String(reference.title ?? reference.source ?? JSON.stringify(reference))}
          </li>
        ))}
      </ul>
    </div>
  )
}
