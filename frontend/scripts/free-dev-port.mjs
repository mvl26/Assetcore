#!/usr/bin/env node
/**
 * Dev-only helper — free the Vite dev port before `vite` starts.
 *
 * Vite dev uses `strictPort: true`, so a leftover dev server (an orphaned
 * `npm run dev` from a previous terminal/session) makes a fresh start fail with
 * "Port 3000 is already in use". This reclaims ONLY a lingering vite process on
 * that port — it never touches an unrelated service.
 *
 * Runs exclusively as the `predev` hook of `npm run dev` (local test env).
 * It is NEVER part of `npm run build` / deploy: production serves the BUILT
 * bundle from assetcore/public/frontend via Frappe and opens no port here.
 *
 * Safe no-op when nothing is listening or when `lsof`/`/proc` are unavailable.
 */
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

const PORT = Number(process.argv[2]) || 3000
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** PIDs LISTENING on the given TCP port (empty if none / lsof missing). */
function pidsOnPort(port) {
  try {
    // execFileSync (no shell) — `port` is already coerced to Number above.
    const out = execFileSync('lsof', ['-ti', `tcp:${port}`, '-sTCP:LISTEN'], {
      stdio: ['ignore', 'pipe', 'ignore'],
    })
      .toString()
      .trim()
    return out ? out.split('\n').map((s) => Number(s.trim())).filter(Boolean) : []
  } catch {
    return [] // lsof exits non-zero when nothing is listening, or isn't installed
  }
}

/** Full command line of a pid via /proc (Linux); '' if unknown. */
function cmdline(pid) {
  try {
    return readFileSync(`/proc/${pid}/cmdline`).toString().replaceAll('\0', ' ').trim()
  } catch {
    return ''
  }
}

/** True if the port is now free (pid gone), false otherwise. */
function isFreed(port, pid) {
  return !pidsOnPort(port).includes(pid)
}

/** Terminate one leftover vite dev server holding the port (SIGTERM → SIGKILL). */
async function reclaim(port, pid) {
  try {
    process.kill(pid, 'SIGTERM')
  } catch {
    return // already gone
  }
  // Wait for the OS to release the socket; escalate if it lingers.
  for (let i = 0; i < 15 && !isFreed(port, pid); i++) await sleep(100)
  if (!isFreed(port, pid)) {
    try {
      process.kill(pid, 'SIGKILL')
    } catch {
      /* gone */
    }
    await sleep(100)
  }
  console.log(`[free-dev-port] freed port ${port} (killed leftover vite dev server, pid ${pid}).`)
}

async function freePort(port) {
  for (const pid of pidsOnPort(port)) {
    if (pid === process.pid) continue
    const cmd = cmdline(pid)
    // Safety gate: only reclaim a leftover vite dev server, never anything else.
    if (cmd && !/vite/i.test(cmd)) {
      console.warn(
        `[free-dev-port] port ${port} held by a non-vite process (pid ${pid}: ${cmd}); leaving it alone.`,
      )
      continue
    }
    await reclaim(port, pid)
  }
}

await freePort(PORT)
