import type common from '../zh-CN/common'

export default {
  app: {
    name: 'WorkNexus',
    tagline: 'AI-native WorkOS',
  },
  nav: {
    home: 'Home',
    projects: 'Projects',
    workChat: 'AI WorkChat',
    skills: 'Skills / MCP',
    audit: 'Audit Log',
    settings: 'Settings',
    members: 'Members',
  },
  actions: {
    close: 'Close',
    confirm: 'Confirm',
    cancel: 'Cancel',
    retry: 'Retry',
    copy: 'Copy',
    done: 'Done',
  },
  errors: {
    requestFailed: 'Request failed, please try again later',
  },
  empty: {
    title: 'No data yet',
  },
  error: {
    title: 'Failed to load',
  },
  userMenu: {
    logout: 'Sign out',
  },
  pagination: {
    previous: 'Previous',
    next: 'Next',
    pageOf: 'Page {{page}} of {{total}}',
  },
  theme: {
    light: 'Light',
    dark: 'Dark',
    system: 'System',
    toggle: 'Toggle theme',
  },
  language: {
    label: 'Language',
    zhCN: '简体中文',
    enUS: 'English',
  },
  home: {
    title: 'Home',
    placeholder: 'Skeleton ready. Business modules under construction.',
  },
} satisfies typeof common
