export default {
  title: 'AI 助手',
  noAccess: '你没有使用该项目 AI 助手的权限',
  thinking: '正在思考…',
  empty: {
    title: '开始与 AI 协作',
    description: '描述你的需求，AI 会回复并在需要写入时生成待确认的动作。',
  },
  input: {
    placeholder: '向 AI 描述需求，回车发送（Shift+回车换行）',
    send: '发送',
  },
  run: {
    failed: 'AI 回合失败',
  },
  status: {
    pending: '待确认',
    approved: '已批准',
    executed: '已执行',
    rejected: '已拒绝',
    failed: '执行失败',
    expired: '已过期',
  },
  actionType: {
    create_work_item: '创建工作项',
    update_work_item: '更新工作项',
    transition_work_item: '流转工作项',
    comment_work_item: '评论工作项',
    create_intake_request: '创建请求',
    accept_intake_request: '接受请求并转化',
  },
  actions: {
    approve: '批准',
    reject: '拒绝',
  },
  knowledge: {
    title: '知识引用',
  },
} as const
