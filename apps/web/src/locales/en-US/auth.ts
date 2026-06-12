import type auth from '../zh-CN/auth'

export default {
  login: {
    title: 'Sign in',
    subtitle: 'Sign in to your workspace with email and password',
    submit: 'Sign in',
  },
  setup: {
    title: 'Set up workspace',
    subtitle: 'First run: create the workspace and the owner account',
    workspaceName: 'Workspace name',
    workspaceNameDefault: 'Default Workspace',
    submit: 'Finish setup',
  },
  invite: {
    title: 'Accept invitation',
    subtitle: 'Set up the account for {{email}} and join the workspace',
    submit: 'Activate and sign in',
    status: {
      accepted: 'This invitation has already been used.',
      expired: 'This invitation has expired. Ask an admin to send a new one.',
      revoked: 'This invitation has been revoked.',
    },
  },
  fields: {
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm password',
    displayName: 'Display name',
  },
  validation: {
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Please enter your password',
    passwordMin: 'Password must be at least 8 characters',
    passwordMismatch: 'Passwords do not match',
    displayNameRequired: 'Please enter a display name',
    workspaceNameRequired: 'Please enter a workspace name',
  },
  errors: {
    invalidCredentials: 'Invalid email or password',
    userDisabled: 'This account has been disabled',
    emailExists: 'This email is already registered or has a pending invitation',
    inviteNotFound: 'Invalid invitation link',
    inviteExpired: 'This invitation has expired',
    inviteAccepted: 'This invitation has already been used',
    inviteRevoked: 'This invitation has been revoked',
    passwordTooWeak: 'Password is too weak (at least 8 characters)',
  },
} satisfies typeof auth
