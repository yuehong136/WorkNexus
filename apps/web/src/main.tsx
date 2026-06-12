import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from '@/app/app'
import { initI18n } from '@/locales/i18n'
import { initUIPreferences, useUIStore } from '@/stores/ui'

import '@/styles/globals.css'

async function bootstrap() {
  initUIPreferences()
  await initI18n(useUIStore.getState().language)
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
