// Copyright (c) 2026, AssetCore Team
// useFormDraft — auto-persist a reactive form to localStorage so users don't
// lose data on reload / accidental tab close. Restore on mount, debounced
// write on every change, explicit clear() after successful submit.
//
// USAGE:
//   const form = ref({ name: '', notes: '' })
//   const { clear } = useFormDraft('purchase-create', form)
//   ...
//   async function submit() {
//     await api.create(form.value)
//     clear()                       // discard draft after success
//     router.push('/purchases')
//   }
//
// NOTES:
//   - The key is auto-namespaced as `assetcore.draft.<key>.v1`.
//   - Restore is skipped if the draft is malformed or version mismatch.
//   - Pass `enabled: false` to disable (e.g., when editing an existing record).
//   - Pass `exclude: ['_internal']` to drop fields from the persisted snapshot.

import { type Ref, type WatchSource, watch, onMounted, onBeforeUnmount } from 'vue'

const PREFIX = 'assetcore.draft.'
const VERSION = 1
const DEFAULT_DEBOUNCE_MS = 400

export interface FormDraftOptions {
  /** Disable persistence entirely (e.g. for edit forms where data is server-loaded). */
  enabled?: boolean
  /** Field names to strip before persisting. */
  exclude?: string[]
  /** Debounce window in ms. Default 400. */
  debounceMs?: number
  /** Auto-clear after this many minutes; 0 disables expiry. Default 1440 (24h). */
  expiryMinutes?: number
}

interface Wrapper<T> {
  v: number
  t: number  // timestamp
  d: T       // data
}

export interface FormDraftHandle {
  clear: () => void
  hasDraft: () => boolean
}

export function useFormDraft<T extends object>(
  key: string,
  formRef: Ref<T>,
  opts: FormDraftOptions = {},
): FormDraftHandle {
  const enabled = opts.enabled !== false
  const debounceMs = opts.debounceMs ?? DEFAULT_DEBOUNCE_MS
  const expiryMs = (opts.expiryMinutes ?? 1440) * 60 * 1000
  const exclude = new Set(opts.exclude ?? [])
  const storageKey = PREFIX + key + '.v' + VERSION

  function read(): T | null {
    if (typeof localStorage === 'undefined') return null
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return null
      const wrap = JSON.parse(raw) as Wrapper<T>
      if (wrap.v !== VERSION) return null
      if (expiryMs > 0 && Date.now() - wrap.t > expiryMs) {
        localStorage.removeItem(storageKey)
        return null
      }
      return wrap.d
    } catch {
      return null
    }
  }

  function write(data: T): void {
    if (typeof localStorage === 'undefined') return
    try {
      const snapshot: Record<string, unknown> = { ...(data as Record<string, unknown>) }
      for (const k of exclude) delete snapshot[k]
      const wrap: Wrapper<unknown> = { v: VERSION, t: Date.now(), d: snapshot }
      localStorage.setItem(storageKey, JSON.stringify(wrap))
    } catch {
      // Quota exceeded or serialization error — silently skip
    }
  }

  function clear(): void {
    if (typeof localStorage === 'undefined') return
    try { localStorage.removeItem(storageKey) } catch { /* ignore */ }
  }

  function hasDraft(): boolean {
    return read() !== null
  }

  let stopWatcher: (() => void) | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  onMounted(() => {
    if (!enabled) return
    const draft = read()
    if (draft) {
      // Shallow merge so newly-added fields in code default in correctly
      Object.assign(formRef.value, draft)
    }
    stopWatcher = watch(
      formRef,
      (next) => {
        if (debounceTimer) clearTimeout(debounceTimer)
        debounceTimer = setTimeout(() => write(next), debounceMs)
      },
      { deep: true },
    )
  })

  onBeforeUnmount(() => {
    if (stopWatcher) stopWatcher()
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      // Flush pending write so navigating-away doesn't lose data
      if (enabled) write(formRef.value)
    }
  })

  return { clear, hasDraft }
}


// ─── Multi-ref variant ──────────────────────────────────────────────────────
// Use when a form is composed of many top-level refs instead of one form ref.
// Pass an object mapping field name → ref; each ref gets restored & watched.

export type FieldsRefs = Record<string, Ref<unknown>>

export function useFieldsDraft(
  key: string,
  fields: FieldsRefs,
  opts: FormDraftOptions = {},
): FormDraftHandle {
  const enabled = opts.enabled !== false
  const debounceMs = opts.debounceMs ?? DEFAULT_DEBOUNCE_MS
  const expiryMs = (opts.expiryMinutes ?? 1440) * 60 * 1000
  const exclude = new Set(opts.exclude ?? [])
  const storageKey = PREFIX + key + '.v' + VERSION

  function snapshot(): Record<string, unknown> {
    const out: Record<string, unknown> = {}
    for (const [name, r] of Object.entries(fields)) {
      if (exclude.has(name)) continue
      out[name] = r.value
    }
    return out
  }

  function read(): Record<string, unknown> | null {
    if (typeof localStorage === 'undefined') return null
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return null
      const wrap = JSON.parse(raw) as Wrapper<Record<string, unknown>>
      if (wrap.v !== VERSION) return null
      if (expiryMs > 0 && Date.now() - wrap.t > expiryMs) {
        localStorage.removeItem(storageKey)
        return null
      }
      return wrap.d
    } catch {
      return null
    }
  }

  function write(): void {
    if (typeof localStorage === 'undefined') return
    try {
      const wrap: Wrapper<unknown> = { v: VERSION, t: Date.now(), d: snapshot() }
      localStorage.setItem(storageKey, JSON.stringify(wrap))
    } catch { /* ignore quota / serialization */ }
  }

  function clear(): void {
    if (typeof localStorage === 'undefined') return
    try { localStorage.removeItem(storageKey) } catch { /* ignore */ }
  }

  function hasDraft(): boolean {
    return read() !== null
  }

  let stops: Array<() => void> = []
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  onMounted(() => {
    if (!enabled) return
    const draft = read()
    if (draft) {
      for (const [name, r] of Object.entries(fields)) {
        if (exclude.has(name)) continue
        if (name in draft) {
          (r as Ref<unknown>).value = draft[name]
        }
      }
    }
    const sources: WatchSource[] = Object.values(fields)
    const stop = watch(
      sources,
      () => {
        if (debounceTimer) clearTimeout(debounceTimer)
        debounceTimer = setTimeout(write, debounceMs)
      },
      { deep: true },
    )
    stops.push(stop)
  })

  onBeforeUnmount(() => {
    for (const stop of stops) stop()
    stops = []
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      if (enabled) write()
    }
  })

  return { clear, hasDraft }
}
