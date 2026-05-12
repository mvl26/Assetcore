// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-06 — Training & Competency Management

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listPrograms, getProgram, createProgram, updateProgram,
  listSessions, getSession, createSession,
  confirmSession, completeSession, cancelSession,
  listCompetencies, getUserCompetencies,
  signoffCompetency, revokeCompetency,
  type TrainingProgram, type TrainingSession,
  type UserCompetency, type TrainingParticipant,
} from '@/api/imm06'
import { ApiError } from '@/api/errors'

export const useImm06Store = defineStore('imm06', () => {
  // Programs state
  const programs = ref<TrainingProgram[]>([])
  const currentProgram = ref<TrainingProgram | null>(null)
  const programPagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  // Sessions state
  const sessions = ref<TrainingSession[]>([])
  const currentSession = ref<TrainingSession | null>(null)
  const sessionPagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  // Competencies state
  const competencies = ref<UserCompetency[]>([])
  const myCompetencies = ref<UserCompetency[]>([])
  const competencyPagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  // Loading / error
  const loading = ref(false)
  const error = ref<string | null>(null)

  function _setError(e: unknown) {
    error.value = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : String(e))
  }

  // Getters
  const activePrograms = computed(() => programs.value.filter(p => p.is_active === 1))
  const upcomingSessions = computed(() =>
    sessions.value.filter(s => s.workflow_state !== 'Cancelled'),
  )

  // ─── Program actions ─────────────────────────────────────────────────────

  async function fetchPrograms(filters = {}, page = 1): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await listPrograms(filters, page)
      programs.value = res.data ?? []
      programPagination.value = res.pagination
    } catch (e: unknown) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchProgram(name: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      currentProgram.value = await getProgram(name)
    } catch (e: unknown) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function doCreateProgram(data: Partial<TrainingProgram>): Promise<string | null> {
    try {
      const res = await createProgram(data)
      return res.name
    } catch (e: unknown) {
      _setError(e)
      return null
    }
  }

  async function doUpdateProgram(
    name: string,
    data: Partial<TrainingProgram>,
  ): Promise<boolean> {
    try {
      await updateProgram(name, data)
      await fetchProgram(name)
      return true
    } catch (e: unknown) {
      _setError(e)
      return false
    }
  }

  // ─── Session actions ──────────────────────────────────────────────────────

  async function fetchSessions(filters = {}, page = 1): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await listSessions(filters, page)
      sessions.value = res.data ?? []
      sessionPagination.value = res.pagination
    } catch (e: unknown) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchSession(name: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      currentSession.value = await getSession(name)
    } catch (e: unknown) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function doCreateSession(data: Record<string, unknown>): Promise<string | null> {
    try {
      const res = await createSession(data)
      return res.name
    } catch (e: unknown) {
      _setError(e)
      return null
    }
  }

  async function doConfirmSession(name: string): Promise<boolean> {
    try {
      await confirmSession(name)
      await fetchSession(name)
      return true
    } catch (e: unknown) {
      _setError(e)
      return false
    }
  }

  async function doCompleteSession(name: string, results: TrainingParticipant[]): Promise<boolean> {
    try {
      await completeSession(name, results)
      await fetchSession(name)
      return true
    } catch (e: unknown) {
      _setError(e)
      return false
    }
  }

  async function doCancelSession(name: string, reason: string): Promise<boolean> {
    try {
      await cancelSession(name, reason)
      await fetchSession(name)
      return true
    } catch (e: unknown) {
      _setError(e)
      return false
    }
  }

  // ─── Competency actions ───────────────────────────────────────────────────

  async function fetchCompetencies(filters = {}, page = 1): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await listCompetencies(filters, page)
      competencies.value = res.data ?? []
      competencyPagination.value = res.pagination
    } catch (e: unknown) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchMyCompetencies(user?: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await getUserCompetencies(user)
      myCompetencies.value = res.competencies
    } catch (e: unknown) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function doSignoffCompetency(name: string): Promise<boolean> {
    try {
      await signoffCompetency(name)
      return true
    } catch (e: unknown) {
      _setError(e)
      return false
    }
  }

  async function doRevokeCompetency(name: string, reason: string, capaRef?: string): Promise<boolean> {
    try {
      await revokeCompetency(name, reason, capaRef)
      return true
    } catch (e: unknown) {
      _setError(e)
      return false
    }
  }

  return {
    // State
    programs, currentProgram, programPagination,
    sessions, currentSession, sessionPagination,
    competencies, myCompetencies, competencyPagination,
    loading, error,
    // Getters
    activePrograms, upcomingSessions,
    // Program actions
    fetchPrograms, fetchProgram, doCreateProgram, doUpdateProgram,
    // Session actions
    fetchSessions, fetchSession, doCreateSession,
    doConfirmSession, doCompleteSession, doCancelSession,
    // Competency actions
    fetchCompetencies, fetchMyCompetencies,
    doSignoffCompetency, doRevokeCompetency,
  }
})
