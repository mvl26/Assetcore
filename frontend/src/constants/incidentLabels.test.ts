// TDD — SUB-BATCH 3b: enum label contract for IMM-12 (incident + RCA).
// Severity = Low/Medium/High/Critical (NOT Major/Minor). Status per BE _STATUS_*.
import { describe, it, expect } from 'vitest'
import {
  incidentSeverityLabel,
  incidentStatusLabel,
  rcaStatusLabel,
  INCIDENT_STATUS_LABEL,
  INCIDENT_SEVERITY_LABEL,
  RCA_STATUS_LABEL,
} from './labels'

describe('IMM-12 incident severity labels (D1)', () => {
  it('maps the 4 BE severities to VI, no Major/Minor', () => {
    expect(incidentSeverityLabel('Low')).toBeTruthy()
    expect(incidentSeverityLabel('Medium')).toBeTruthy()
    expect(incidentSeverityLabel('High')).toBe('Cao')
    expect(incidentSeverityLabel('Critical')).toBeTruthy()
    // legacy enum must NOT be a recognized key
    expect(INCIDENT_SEVERITY_LABEL).not.toHaveProperty('Major')
    expect(INCIDENT_SEVERITY_LABEL).not.toHaveProperty('Minor')
  })

  it('every VI severity label has no raw English token', () => {
    for (const v of ['Low', 'Medium', 'High', 'Critical']) {
      const label = incidentSeverityLabel(v)
      expect(label).not.toMatch(/\b(Major|Minor|Low|Medium|High|Critical)\b/)
    }
  })
})

describe('IMM-12 incident status labels (D2 + D3)', () => {
  it('covers full BE state machine incl. Acknowledged (D3)', () => {
    for (const s of ['Open', 'Acknowledged', 'In Progress', 'Resolved', 'RCA Required', 'Closed', 'Cancelled']) {
      expect(INCIDENT_STATUS_LABEL).toHaveProperty(s)
      expect(incidentStatusLabel(s)).not.toMatch(/\b(Reported|Submitted)\b/)
    }
  })

  it('has no legacy Reported/Submitted keys', () => {
    expect(INCIDENT_STATUS_LABEL).not.toHaveProperty('Reported')
    expect(INCIDENT_STATUS_LABEL).not.toHaveProperty('Submitted')
  })
})

describe('IMM-12 RCA status labels (new for /rca list)', () => {
  it('covers the 4 RCA states with VI labels', () => {
    for (const s of ['RCA Required', 'RCA In Progress', 'Completed', 'Cancelled']) {
      expect(RCA_STATUS_LABEL).toHaveProperty(s)
      expect(rcaStatusLabel(s)).toBeTruthy()
    }
  })
})
