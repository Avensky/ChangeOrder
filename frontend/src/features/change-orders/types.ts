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
  status: "submitted" | "awaiting_client" | "approved" | "rejected";
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
