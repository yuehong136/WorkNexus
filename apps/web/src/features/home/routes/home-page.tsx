import { useTranslation } from 'react-i18next'

export function HomePage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <h1 className="text-xl font-semibold text-text-primary">{t('home.title')}</h1>
      <p className="text-sm text-text-secondary">{t('home.placeholder')}</p>
    </div>
  )
}
