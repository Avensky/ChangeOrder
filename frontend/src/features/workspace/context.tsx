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
  roles,
  seedChanges,
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
  const [unread, setUnread] = useState(3);
  const events = changes
    .flatMap((change) => change.history)
    .sort((a, b) => Date.parse(b.time) - Date.parse(a.time));

  function update(
    id: string,
    status: ChangeStatus,
    title: string,
    extras: Partial<WorkspaceChange> = {},
  ) {
    const event: Event = {
      id: "event-" + Date.now(),
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
    setUnread((count) => count + 1);
  }

  async function create(input: NewChange) {
    // Demo submissions stay local. Connected submissions retain the working API upload.
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
      author: roles.field.person,
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
          person: roles.field.person,
          time,
          kind: "submitted",
        },
      ],
    };
    setChanges((items) => [record, ...items]);
    setUnread((count) => count + 1);
    return record;
  }

  async function review(id: string, amount: number, days: number) {
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
        ? "Urgent change approved by office"
        : "Sent to client for approval",
      { amount, impactDays: days },
    );
  }

  async function decide(id: string, approved: boolean) {
    const record = changes.find((change) => change.id === id);
    if (!record || record.status !== "awaiting_client")
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
        throw new Error("The client approval link could not be found.");
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
      approved ? "Change approved by client" : "Change declined by client",
    );
  }

  function reset() {
    setChanges(seedChanges());
    setUnread(3);
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
        changes,
        events,
        unread,
        markRead: () => setUnread(0),
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
