export default {
  login: {
    title: '登录',
    subtitle: '使用邮箱和密码登录工作区',
    submit: '登录',
  },
  setup: {
    title: '初始化工作区',
    subtitle: '首次启动：创建工作区与 Owner 账号',
    workspaceName: '工作区名称',
    workspaceNameDefault: 'Default Workspace',
    submit: '完成初始化',
  },
  invite: {
    title: '接受邀请',
    subtitle: '为 {{email}} 设置账号信息并加入工作区',
    submit: '激活并登录',
    status: {
      accepted: '该邀请已被使用。',
      expired: '该邀请已过期，请联系管理员重新发起邀请。',
      revoked: '该邀请已被撤销。',
    },
  },
  fields: {
    email: '邮箱',
    password: '密码',
    confirmPassword: '确认密码',
    displayName: '显示名称',
  },
  validation: {
    emailInvalid: '请输入有效的邮箱地址',
    passwordRequired: '请输入密码',
    passwordMin: '密码至少 8 位',
    passwordMismatch: '两次输入的密码不一致',
    displayNameRequired: '请输入显示名称',
    workspaceNameRequired: '请输入工作区名称',
  },
  errors: {
    invalidCredentials: '邮箱或密码错误',
    userDisabled: '该账号已被禁用',
    emailExists: '该邮箱已被注册或已有待处理的邀请',
    inviteNotFound: '邀请链接无效',
    inviteExpired: '邀请已过期',
    inviteAccepted: '邀请已被使用',
    inviteRevoked: '邀请已被撤销',
    passwordTooWeak: '密码强度不足（至少 8 位）',
  },
}
