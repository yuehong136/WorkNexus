export default {
  title: 'AI Assistant',
  noAccess: 'You do not have permission to use this project’s AI assistant',
  thinking: 'Thinking…',
  empty: {
    title: 'Start collaborating with AI',
    description: 'Describe what you need; the AI replies and proposes confirmable actions when it wants to write.',
  },
  input: {
    placeholder: 'Describe what you need, press Enter to send (Shift+Enter for newline)',
    send: 'Send',
  },
  run: {
    failed: 'AI run failed',
  },
  status: {
    pending: 'Pending',
    approved: 'Approved',
    executed: 'Executed',
    rejected: 'Rejected',
    failed: 'Failed',
    expired: 'Expired',
  },
  actionType: {
    create_work_item: 'Create work item',
    update_work_item: 'Update work item',
    transition_work_item: 'Transition work item',
    comment_work_item: 'Comment on work item',
  },
  actions: {
    approve: 'Approve',
    reject: 'Reject',
  },
  knowledge: {
    title: 'Knowledge references',
  },
} as const
