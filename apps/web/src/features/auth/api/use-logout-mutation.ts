import { useMutation, useQueryClient } from '@tanstack/react-query'
import { logout } from '@worknexus/contracts'

export function useLogoutMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await logout()
    },
    onSuccess: () => {
      // resetQueries (not clear): active observers refetch, so the me query
      // 401s and RequireAuth redirects to /login.
      void queryClient.resetQueries()
    },
  })
}
