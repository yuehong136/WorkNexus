import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export default function globalSetup() {
  const serverDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../server')
  execSync('uv run python scripts/e2e_reset_db.py', { cwd: serverDir, stdio: 'inherit' })
}
