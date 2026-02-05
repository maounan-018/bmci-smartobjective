
export enum UserRole {
  COLLAB = 'COLLAB',
  MANAGER = 'MANAGER',
  HR = 'HR'
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  team?: string;
  entity?: string;
  manager_id?: string;
}

export interface SmartIssue {
  letter: 'S' | 'M' | 'A' | 'R' | 'T';
  problem: string;
  fix: string;
}

export interface SmartAnalysis {
  S: boolean;
  M: boolean;
  A: boolean;
  R: boolean;
  T: boolean;
  overall: boolean;
  confidence: number;
  issues: SmartIssue[];
  rewrite_fr: string;
  rewrite_en: string;
}

export interface CompanyObjective {
  id: string;
  title: string;
  description: string;
  department?: string;
  priority?: number;
  weight?: number;
}

export interface AlignmentMatch {
  objective_id: string;
  score: number;
  reason: string;
}

export interface AlignmentAnalysis {
  alignment_score: number;
  top_matches: AlignmentMatch[];
  gaps: string[];
}

export interface Objective {
  id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  title: string;
  description: string;
  context?: string;
  entity?: string;
  manager_name?: string;
  period?: string;
  status: 'draft' | 'analyzed' | 'validated';
  progress: 'not_started' | 'in_progress' | 'completed' | 'on_hold';
  smartAnalysis?: SmartAnalysis;
  alignmentAnalysis?: AlignmentAnalysis;
  smart_score?: number;
  alignment_score?: number;
  s_score?: number;
  m_score?: number;
  a_score?: number;
  r_score?: number;
  t_score?: number;
  issues_count?: number;
  top_issue?: string;
  createdAt: string;
}

// ============= HR Module Types =============

export interface HRImport {
  id: string;
  import_type: 'strategy' | 'objectives';
  filename: string;
  records_count: number;
  user_id: string;
  created_at: string;
}

export interface HRAnalytics {
  global_stats: {
    total: number;
    analyzed: number;
    validated: number;
  };
  avg_scores: {
    avg_smart: number | null;
    avg_alignment: number | null;
    avg_s: number | null;
    avg_m: number | null;
    avg_a: number | null;
    avg_r: number | null;
    avg_t: number | null;
  };
  smart_evolution: Array<{ month: string; avg_smart: number; count: number }>;
  alignment_evolution: Array<{ month: string; avg_alignment: number; count: number }>;
  smart_distribution: Array<{ level: string; count: number }>;
  alignment_distribution: Array<{ level: string; count: number }>;
  blocking_points: Array<{ criteria: string; failures: number }>;
  entity_comparison: Array<{ entity: string; avg_smart: number; avg_alignment: number; count: number }>;
  manager_comparison: Array<{ manager: string; avg_smart: number; avg_alignment: number; count: number }>;
  period_comparison: Array<{ period: string; avg_smart: number; avg_alignment: number; count: number }>;
  filters: {
    entities: string[];
    managers: string[];
    periods: string[];
  };
}

export interface HRObjectiveDetail extends Objective {
  smart_analysis?: SmartAnalysis | string;
  alignment_analysis?: AlignmentAnalysis | string;
  user_name?: string;
  entity?: string;
  manager_name?: string;
  period?: string;
  smart_score?: number;
  alignment_score?: number;
  s_score?: number;
  m_score?: number;
  a_score?: number;
  r_score?: number;
  t_score?: number;
  rewrite_fr?: string;
  rewrite_en?: string;
  analyzed_at?: string;
}

export interface BatchAnalysisResult {
  id: string;
  title: string;
  smart_score?: number;
  alignment_score?: number;
  success: boolean;
  error?: string;
}
