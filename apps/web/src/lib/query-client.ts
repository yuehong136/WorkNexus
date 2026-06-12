import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { APIError } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'
import i18n from '@/locales/i18n'

declare module '@tanstack/react-query' {
  interface Register {
    mutationMeta: {
      /** Set when the component renders the error inline (e.g. forms). */
      suppressToast?: boolean
    }
  }
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof APIError && error.status === 401
}

/** Drop the cached identity so RequireAuth re-evaluates and redirects to /login. */
function resetIdentity() {
  void queryClient.resetQueries({ queryKey: authKeys.me() })
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      // The me query erroring IS the signal the guards consume — only react
      // when some other query hits a stale session.
      if (isUnauthorized(error) && query.queryKey[0] !== authKeys.all[0]) {
        resetIdentity()
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (isUnauthorized(error)) {
        resetIdentity()
      }
      if (mutation.meta?.suppressToast) return
      toast.error(error instanceof APIError ? error.message : i18n.t('errors.requestFailed'))
    },
  }),
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => !isUnauthorized(error) && failureCount < 1,
      staleTime: 30_000,
    },
  },
})
