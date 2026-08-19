export type TabType = 
  | 'risk' 
  | 'remediation' 
  | 'audit' 
  | 'search' 
  | 'ingest' 
  | 'chat' 
  | 'mcp';

export type ExposureLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface ActionItem {
  phase: string;
  action: string;
  deadline_days: number;
  statutory_ref: string;
  est_cost_usd?: number;
}

export interface RiskAnalysisResult {
  exposure_level: ExposureLevel;
  priority_rank: number;
  confidence_score: number;
  statutory_rationale: string;
  actionable_roadmap: ActionItem[];
}

export interface RemediationStep {
  step_number: number;
  phase: string;
  title: string;
  action: string;
  timeline_days: number;
  est_cost_usd: number;
  owner_role: string;
  statutory_reference: string;
}

export interface RemediationResult {
  risk_title: string;
  total_est_cost_usd: number;
  total_duration_days: number;
  remediation_steps: RemediationStep[];
}

export type AuditMode = 'quick_review' | 'full_audit' | 'forensic_audit';

export interface AuditFinding {
  rule_code: string;
  category: string;
  severity: ExposureLevel;
  status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'NOT_APPLICABLE';
  description: string;
  recommended_remediation: string;
  evidence_required: string[];
}

export interface LegalAuditResult {
  audit_id: string;
  timestamp: string;
  overall_recommendation: 'APPROVE' | 'APPROVE_WITH_CONDITIONS' | 'DO_NOT_APPROVE';
  confidence_score: number;
  findings: AuditFinding[];
  summary_executive: string;
  key_statutory_violations: string[];
  max_penalty_exposure_inr: string;
}

export interface SearchResultChunk {
  chunk_id: string;
  statute: string;
  section: string;
  text: string;
  similarity_score: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
}
