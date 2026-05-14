// Copyright (c) 2026, AssetCore Team
// v-permission directive — ẩn/xoá element khi user không đủ role.
//
// Usage:
//   <button v-permission="'IMM System Admin'">…</button>
//   <button v-permission="['IMM QA Officer', 'IMM System Admin']">…</button>

import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

type PermValue = string | readonly string[]

function allowed(value: PermValue): boolean {
  const auth = useAuthStore()
  const required = Array.isArray(value) ? value : [value as string]
  return required.length === 0 || auth.hasAnyRole(required)
}

function enforce(el: HTMLElement, binding: DirectiveBinding<PermValue>) {
  if (!allowed(binding.value)) {
    el.parentNode?.removeChild(el)
  }
}

export const vPermission: Directive<HTMLElement, PermValue> = {
  mounted: enforce,
  updated: enforce,
}
