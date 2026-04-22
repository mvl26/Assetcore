export type RepairStatus =
  | 'Open'
  | 'Assigned'
  | 'Diagnosing'
  | 'Pending Parts'
  | 'In Repair'
  | 'Pending Inspection'
  | 'Completed'
  | 'Cannot Repair'
  | 'Cancelled'

export type RepairPriority = 'Normal' | 'Urgent' | 'Emergency'

export type { AssetRepair, SparePartRow, RepairChecklistRow, RepairKPIs, RepairListResponse, MttrReport } from '@/api/imm09'
