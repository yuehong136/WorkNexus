import { QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { APIError } from '@/lib/api-client'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
    mutations: {
      onError: (error) => {
        toast.error(error instanceof APIError ? error.message : 'Request failed')
      },
    },
  },
})
