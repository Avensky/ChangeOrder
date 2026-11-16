export type Severity = "normal" | "high";
export type Suggestion = {
  scope: string;
  amount: number;
  impact_days: number;
  rationale: string;
  in_scope: boolean;
};
export type ChangeOrder = {
  id: string;
  code: string;
  title: string;
  project_id: string;
  submitted_by: "contractor" | "subcontractor";
  author: string;
  created_at: string;
  description: string;
  severity: Severity;
  status: "submitted" | "in_review" | "authorized_to_proceed" | "awaiting_gc" | "approved" | "declined" | "withdrawn";
  proposed_cost_cents?: number | null;
  requested_timeline_days?: number | null;
  currency?: string;
  photo_keys: string[];
  amount: number;
  impact_days: number;
  sent_for_approval: boolean;
  approved_scope: string | null;
  history: {
    id: string;
    changeId: string;
    title: string;
    person: string;
    time: string;
    kind: string;
  }[];
  suggestion: Suggestion | null;
};
