export const homeKeys = {
  all: ['home'] as const,
  snapshot: () => [...homeKeys.all, 'snapshot'] as const,
}
