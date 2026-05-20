<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Trang /admin/roles — catalog 30 role + grid gan role cho user.
// Gate: meta.requiredCapabilities = ['data.admin'] (router) + BE rbac.require.

import { ref, computed, onMounted } from 'vue'
import { ROLE_CATALOG, SYSTEM_ROLES, DOMAINS } from '@/constants/roles'
import {
  listUsers, getUserRoles, setUserRoles,
  type SimpleUser,
} from '@/api/roleAdmin'

const users = ref<SimpleUser[]>([])
const selected = ref<string>('')
const assigned = ref<Set<string>>(new Set())
const saving = ref(false)
const loading = ref(false)
const message = ref<string>('')
const search = ref<string>('')

const filteredUsers = computed(() => {
  const s = search.value.trim().toLowerCase()
  if (!s) return users.value
  return users.value.filter(
    (u) =>
      u.name.toLowerCase().includes(s) ||
      (u.full_name ?? '').toLowerCase().includes(s),
  )
})

onMounted(async () => {
  loading.value = true
  try {
    users.value = await listUsers()
  } finally {
    loading.value = false
  }
})

async function pick(u: string) {
  selected.value = u
  message.value = ''
  const all = await getUserRoles(u)
  assigned.value = new Set(all)
}

function toggle(role: string) {
  if (assigned.value.has(role)) assigned.value.delete(role)
  else assigned.value.add(role)
  assigned.value = new Set(assigned.value)
}

async function save() {
  if (!selected.value) return
  saving.value = true
  message.value = ''
  try {
    const acNames = new Set(ROLE_CATALOG.map((r) => r.name))
    const acAssigned = [...assigned.value].filter((r) => acNames.has(r))
    const res = await setUserRoles(selected.value, acAssigned)
    assigned.value = new Set(res.roles ?? [])
    message.value = 'Đã lưu phân quyền.'
  } catch (e) {
    message.value = `Lỗi: ${(e as Error).message}`
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="p-6 space-y-8">
    <h1 class="text-xl font-semibold">Phân quyền theo module</h1>

    <!-- ── 1. Catalog 30 role ──────────────────────────────────────── -->
    <section>
      <h2 class="font-medium mb-2">Danh mục Role và quyền</h2>
      <div class="border rounded overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-slate-100 text-left">
              <th class="p-2">Role</th>
              <th class="p-2">Nhóm</th>
              <th class="p-2">Mô tả quyền</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in ROLE_CATALOG" :key="r.name" class="border-t">
              <td class="p-2 font-mono">{{ r.name }}</td>
              <td class="p-2">{{ r.group }}</td>
              <td class="p-2 text-slate-600">{{ r.description }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── 2. Gán role cho user ────────────────────────────────────── -->
    <section>
      <h2 class="font-medium mb-2">Gán role cho người dùng</h2>
      <div class="grid grid-cols-3 gap-4">
        <!-- Cột trái: danh sách user -->
        <div class="col-span-1 border rounded">
          <input
            v-model="search"
            placeholder="Tìm người dùng…"
            class="w-full p-2 border-b text-sm"
          />
          <div class="max-h-96 overflow-auto">
            <div v-if="loading" class="p-4 text-sm text-slate-500">
              Đang tải…
            </div>
            <button
              v-for="u in filteredUsers"
              :key="u.name"
              type="button"
              class="block w-full text-left p-2 hover:bg-slate-50 border-t"
              :class="{ 'bg-blue-50': selected === u.name }"
              @click="pick(u.name)"
            >
              <div class="font-medium">{{ u.full_name || u.name }}</div>
              <div class="text-xs text-slate-500">{{ u.name }}</div>
            </button>
          </div>
        </div>

        <!-- Cột phải: grid Manager/User × module + System -->
        <div v-if="selected" class="col-span-2 space-y-4">
          <div>
            <h3 class="font-medium mb-1">System Roles</h3>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="s in SYSTEM_ROLES"
                :key="s"
                class="inline-flex items-center gap-1 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="assigned.has(s)"
                  @change="toggle(s)"
                />
                <span>{{ s }}</span>
              </label>
            </div>
          </div>

          <div>
            <h3 class="font-medium mb-1">Module Roles</h3>
            <table class="text-sm border w-full">
              <thead>
                <tr class="bg-slate-100">
                  <th class="p-2 text-left">Module</th>
                  <th class="p-2">Manager</th>
                  <th class="p-2">User</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in DOMAINS" :key="d" class="border-t">
                  <td class="p-2">{{ d }}</td>
                  <td class="p-2 text-center">
                    <input
                      type="checkbox"
                      :checked="assigned.has(`${d} Manager`)"
                      @change="toggle(`${d} Manager`)"
                    />
                  </td>
                  <td class="p-2 text-center">
                    <input
                      type="checkbox"
                      :checked="assigned.has(`${d} User`)"
                      @change="toggle(`${d} User`)"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex items-center gap-3">
            <button
              type="button"
              class="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? 'Đang lưu…' : 'Lưu phân quyền' }}
            </button>
            <span v-if="message" class="text-sm text-slate-600">
              {{ message }}
            </span>
          </div>
        </div>

        <div v-else class="col-span-2 text-slate-500 text-sm">
          Chọn 1 người dùng ở cột trái để bắt đầu gán role.
        </div>
      </div>
    </section>
  </div>
</template>
