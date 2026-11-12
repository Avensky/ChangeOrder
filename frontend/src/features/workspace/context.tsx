import type { ImagePickerAsset } from "expo-image-picker";
import { createContext, type ReactNode, useContext, useState } from "react";

import { submitChange } from "@/features/change-orders/api";
import type { Severity } from "@/features/change-orders/types";
import { API_URL, requestJson } from "@/lib/api";

import {
  type ChangeStatus,
  type Event,
  type Mode,
  type Role,
  type WorkspaceChange,
  canViewChange,
  isSubmitterRole,
  roles,
  seedChanges,
  visibleHistory,
} from "./data";

type NewChange = {
  title: string;
  description: string;
  severity: Severity;
  projectId: string;
  photo: ImagePickerAsset;
};
type Workspace = {
  role: Role;
  setRole: (role: Role) => void;
  mode: Mode;
  setMode: (mode: Mode) => void;
  changes: WorkspaceChange[];
  events: Event[];
  unread: number;
  markRead: () => void;
  create: (input: NewChange) => Promise<WorkspaceChange>;
  review: (id: string, amount: number, days: number) => Promise<void>;
  decide: (id: string, approved: boolean) => Promise<void>;
  reset: () => void;
};
const WorkspaceContext = createContext<Workspace | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>("office");
  const [mode, setMode] = useState<Mode>("demo");
  const [changes, setChanges] = useState(seedChanges);
  const [readEvents, setReadEvents] = useState<
    Partial<Record<Role, Set<string>>>
  >({});
  const visibleChanges = changes.filter((change) => canViewChange(role, change));
  const events = visibleChanges
    .flatMap((change) => visibleHistory(role, change))
    .sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
  const unread = events.filter((event) => !readEvents[role]?.has(event.id)).length;

  function update(
    id: string,
    status: ChangeStatus,
    title: string,
    extras: Partial<WorkspaceChange> = {},
  ) {
    const event: Event = {
      id: `${id}-${status}`,
      changeId: id,
      title,
      person: roles[role].person,
      time: new Date().toISOString(),
      kind: status,
    };
    setChanges((items) =>
      items.map((change) =>
        change.id === id
          ? {
              ...change,
              ...extras,
              status,
              history: [...change.history, event],
            }
          : change,
      ),
    );
  }

  async function create(input: NewChange) {
    if (!isSubmitterRole(role))
      throw new Error("Switch to Contractor or Subcontractor to submit a change.");
    // Connected mode uses the same upload contract as the existing workspace.
    const result =
      mode === "connected"
        ? await submitChange(input.description, input.severity, input.photo)
        : null;
    const id = result?.id ?? "demo-" + Date.now().toString(36);
    const time = new Date().toISOString();
    const record: WorkspaceChange = {
      id,
      code: "CO-" + (1049 + Math.max(0, changes.length - 8)),
      title: input.title.trim(),
      description: result?.description ?? input.description.trim(),
      projectId: input.projectId,
      severity: input.severity,
      status: result?.status ?? "submitted",
      amount: 0,
      impactDays: 0,
      author: roles[role].person,
      submittedBy: role,
      sentForApproval: false,
      createdAt: time,
      source: mode,
      photoUri: result?.photo_key
        ? API_URL + "/uploads/" + result.photo_key
        : input.photo.uri,
      history: [
        {
          id: id + "-submitted",
          changeId: id,
          title: "Change request submitted",
          person: roles[role].person,
          time,
          kind: "submitted",
        },
      ],
    };
    setChanges((items) => [record, ...items]);
    return record;
  }

  async function review(id: string, amount: number, days: number) {
    if (role !== "office")
      throw new Error("Switch to Office Manager to review a change.");
    const record = changes.find((change) => change.id === id);
    if (!record || record.status !== "submitted")
      throw new Error("This request has already been reviewed.");
    let status: ChangeStatus =
      record.severity === "high" ? "approved" : "awaiting_client";
    if (record.source === "connected") {
      const result = await requestJson<{ status: ChangeStatus }>(
        "/api/v1/changes/" + encodeURIComponent(id) + "/admin-approve",
        { method: "POST" },
      );
      status = result.status;
    }
    update(
      id,
      status,
      status === "approved"
        ? "Urgent change approved by Office Manager"
        : "Sent to approver",
      { amount, impactDays: days, sentForApproval: status === "awaiting_client" },
    );
  }

  async function decide(id: string, approved: boolean) {
    if (role !== "approver")
      throw new Error("Switch to Approver to record a decision.");
    const record = changes.find((change) => change.id === id);
    if (!record?.sentForApproval || record.status !== "awaiting_client")
      throw new Error("This request is no longer awaiting a decision.");
    if (record.source === "connected") {
      const notices = await requestJson<{ change_id: string; msg: string }[]>(
        "/api/v1/notifications?to=client",
      );
      const link = notices
        .filter((notice) => notice.change_id === id)
        .at(-1)?.msg;
      const token = link ? new URL(link).searchParams.get("token") : null;
      if (!token)
        throw new Error("The approval link could not be found.");
      await requestJson(
        "/api/v1/approval-session/" +
          (approved ? "approve" : "decline") +
          "?token=" +
          encodeURIComponent(token),
        { method: "POST" },
      );
    }
    update(
      id,
      approved ? "approved" : "rejected",
      approved ? "Change approved" : "Change declined",
    );
  }

  function reset() {
    setChanges(seedChanges());
    setReadEvents({});
    setMode("demo");
    setRole("office");
  }

  return (
    <WorkspaceContext.Provider
      value={{
        role,
        setRole,
        mode,
        setMode,
        changes: visibleChanges,
        events,
        unread,
        markRead: () =>
          setReadEvents((current) => ({
            ...current,
            [role]: new Set(events.map((event) => event.id)),
          })),
        create,
        review,
        decide,
        reset,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("WorkspaceProvider is required.");
  return value;
}
