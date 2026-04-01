/**
 * inject-token.js — Bakes POSTHOG_TOKEN into the compiled analytics module.
 *
 * Must run AFTER `tsc` and BEFORE electron-builder packages the app.
 * In CI the env var is set via GitHub Actions secret; locally it is empty,
 * which keeps analytics as a silent no-op (same behaviour as before).
 */
'use strict'

const fs   = require('fs')
const path = require('path')

const target = path.join(__dirname, '../dist/main/analytics.js')

if (!fs.existsSync(target)) {
  console.error(`inject-token: target not found: ${target}`)
  console.error('Run `npm run build` before inject-token.')
  process.exit(1)
}

const token    = process.env.POSTHOG_TOKEN || ''
const tokenLit = JSON.stringify(token)           // e.g. '"abc123"' or '""'

let src = fs.readFileSync(target, 'utf-8')
src = src.replace(/process\.env\.POSTHOG_TOKEN/g, tokenLit)
fs.writeFileSync(target, src, 'utf-8')

console.log(`inject-token: POSTHOG_TOKEN ${token ? 'injected ✓' : 'empty (no-op build)'}`)
