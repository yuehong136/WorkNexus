import { defineConfig } from 'orval'

export default defineConfig({
  worknexus: {
    input: '../../apps/server/openapi.json',
    output: {
      target: 'src/api.ts',
      schemas: 'src/model',
      client: 'react-query',
      httpClient: 'fetch',
      override: {
        mutator: {
          path: 'src/mutator.ts',
          name: 'apiMutator',
        },
      },
    },
  },
})
