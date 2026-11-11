// Match backend/schemas/changes.py. Priority is named severity in the API.
export type Severity = 'normal' | 'high';

export type ChangeOrder = {
  id: string;
  description: string;
  severity: Severity;
  status: 'submitted' | 'awaiting_client' | 'approved' | 'rejected';
  photo_key: string | null;
};
