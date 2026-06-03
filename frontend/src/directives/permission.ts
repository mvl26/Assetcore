// Copyright (c) 2026, AssetCore Team
// v-can / v-permission directive — an/xoa element khi user thieu capability.
// UX only — BE rbac.require moi la chot chan.
//
// Usage:
//   <button v-can="'pm.write'">...</button>
//   <button v-can="['pm.write','repair.write']">...</button>
//
// Legacy v-permission van duoc dang ky alias trong main.ts (cung handler) de
// view chua refactor khong vo. Khi value la 1 role-name (legacy persona), check
// truoc xem co la capability hop le khong; neu khong, fallback sang hasRole.

import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

type CanValue = string | readonly string[]

function isCapability(v: string): boolean {
  // Capability key luon co dot, vd "pm.write", "doc.approve", "data.admin"
  return v.includes('.')
}

function ok(value: CanValue): boolean {
  const auth = useAuthStore()
  const required = Array.isArray(value) ? value : [value as string]
  if (required.length === 0) return true
  return required.some((v) => (isCapability(v) ? auth.can(v) : auth.hasRole(v)))
}

function enforce(el: HTMLElement, binding: DirectiveBinding<CanValue>) {
  if (!ok(binding.value)) {
    el.parentNode?.removeChild(el)
  }
}

export const vCan: Directive<HTMLElement, CanValue> = {
  mounted: enforce,
  updated: enforce,
}

// Legacy alias — view cu dung v-permission van chay
export const vPermission = vCan
