import type { ChangeOrder, Severity } from "@/features/change-orders/types";

export type Role = "manager" | "contractor" | "subcontractor" | "office" | "approver";
export type SubmitterRole = Extract<Role, "contractor" | "subcontractor">;
export type Mode = "demo" | "connected";
export type ChangeStatus = ChangeOrder["status"];
export type Project = {
  id: string;
  name: string;
  address: string;
  client: string;
  budget: number;
  progress: number;
  initials: string;
  color: string;
};
export type Event = {
  id: string;
  changeId: string;
  title: string;
  person: string;
  time: string;
  kind: string;
};
export type WorkspaceChange = {
  id: string;
  code: string;
  title: string;
  description: string;
  projectId: string;
  severity: Severity;
  status: ChangeStatus;
  amount: number;
  approvedScope?: string | null;
  impactDays: number;
  author: string;
  submittedBy: SubmitterRole;
  sentForApproval: boolean;
  createdAt: string;
  source: Mode;
  photoUri?: string;
  photoUris?: string[];
  suggestion?: import("@/features/change-orders/types").Suggestion | null;
  history: Event[];
};

export const roles: Record<
  Role,
  { label: string; person: string; initials: string; caption: string }
> = {
  manager: { label: "Manager", person: "Demo Manager", initials: "DM", caption: "Authorize urgent work before estimation" },
  contractor: {
    label: "Contractor",
    person: "Uriel Zacarias",
    initials: "UZ",
    caption: "Coordinate changes across projects",
  },
  subcontractor: {
    label: "Field",
    person: "Marcus Rivera",
    initials: "MR",
    caption: "Report site changes and track submissions",
  },
  office: {
    label: "Estimator",
    person: "Avery Morgan",
    initials: "AM",
    caption: "Review requests and prepare terms",
  },
  approver: {
    label: "GC preview",
    person: "Jordan Ellis",
    initials: "JE",
    caption: "Review terms and record decisions",
  },
};

export function isSubmitterRole(role: Role): role is SubmitterRole {
  return role === "contractor" || role === "subcontractor";
}

export function canViewChange(role: Role, change: WorkspaceChange) {
  if (role === "subcontractor") return change.submittedBy === role;
  if (role === "approver") return change.sentForApproval;
  return true;
}

export function visibleHistory(role: Role, change: WorkspaceChange) {
  return role === "approver"
    ? change.history.filter(
        (event) =>
          event.kind === "awaiting_gc" ||
          event.kind === "approved" ||
          event.kind === "declined",
      )
    : change.history;
}

export const projects: Project[] = [
  {
    id: "north-park",
    name: "North Park Residence",
    address: "North Park · San Diego, CA",
    client: "Jordan Ellis",
    budget: 185000,
    progress: 68,
    initials: "NP",
    color: "#E6EEDC",
  },
  {
    id: "harbor",
    name: "Harbor Office Fit-out",
    address: "Downtown · San Diego, CA",
    client: "Harbor Studio",
    budget: 320000,
    progress: 42,
    initials: "HO",
    color: "#E2EAF1",
  },
  {
    id: "cedar",
    name: "Cedar Ridge Duplex",
    address: "La Mesa · San Diego, CA",
    client: "Ridge Development",
    budget: 245000,
    progress: 81,
    initials: "CR",
    color: "#F0E6D8",
  },
];

const rows: [
  string,
  string,
  string,
  string,
  Severity,
  ChangeStatus,
  number,
  number,
][] = [
  [
    "1048",
    "Kitchen outlet relocation",
    "Move the kitchen outlet 12 inches left to clear the revised cabinet layout. Existing wiring can be reused.",
    "north-park",
    "normal",
    "submitted",
    450,
    0,
  ],
  [
    "1047",
    "Additional waterproofing",
    "Add a waterproof membrane at the shower niche before tiling. The existing detail leaves the corners exposed.",
    "cedar",
    "high",
    "submitted",
    1250,
    1,
  ],
  [
    "1046",
    "Upgrade lobby lighting",
    "Replace the specified lobby fixtures with dimmable recessed lights to match the revised lighting plan.",
    "harbor",
    "normal",
    "awaiting_gc",
    2400,
    1,
  ],
  [
    "1045",
    "Patio door opening adjustment",
    "Widen the framed opening to accommodate the owner-selected sliding door.",
    "north-park",
    "normal",
    "approved",
    1800,
    1,
  ],
  [
    "1044",
    "Replace damaged subfloor",
    "Replace the water-damaged subfloor section discovered during bathroom demolition.",
    "cedar",
    "high",
    "approved",
    950,
    1,
  ],
  [
    "1043",
    "Add conference room outlets",
    "Provide two additional floor outlets below the conference table.",
    "harbor",
    "normal",
    "awaiting_gc",
    680,
    0,
  ],
  [
    "1042",
    "Custom kitchen shelving",
    "Add three floating oak shelves beside the range hood.",
    "north-park",
    "normal",
    "declined",
    720,
    0,
  ],
  [
    "1041",
    "Laundry plumbing adjustment",
    "Move the laundry water connections to align with the final appliance locations.",
    "cedar",
    "normal",
    "approved",
    560,
    0,
  ],
];

export function seedChanges(): WorkspaceChange[] {
  return rows.map(
    (
      [
        number,
        title,
        description,
        projectId,
        severity,
        status,
        amount,
        impactDays,
      ],
      i,
    ) => {
      const id = "demo-" + number;
      const time = `2026-10-${String(22 - Math.floor(i / 2)).padStart(2, "0")}T${String(16 - i).padStart(2, "0")}:20:00-07:00`;
      const submittedBy = i % 2 ? "subcontractor" : "contractor";
      const sentForApproval =
        status === "awaiting_gc" ||
        status === "declined" ||
        status === "approved";
      const history: Event[] = [
        {
          id: id + "-submitted",
          changeId: id,
          title: "Change request submitted",
          person: roles[submittedBy].person,
          time,
          kind: "submitted",
        },
      ];
      if (status !== "submitted")
        history.push({
          id: id + "-review",
          changeId: id,
          title: sentForApproval
            ? "Sent to approver"
            : "Office review completed",
          person: roles.office.person,
          time,
          kind: sentForApproval ? "awaiting_gc" : "review",
        });
      if (status === "approved" || status === "declined")
        history.push({
          id: id + "-decision",
          changeId: id,
          title: status === "approved" ? "Change approved" : "Change declined",
          person: roles[sentForApproval ? "approver" : "office"].person,
          time,
          kind: status,
        });
      return {
        id,
        code: "CO-" + number,
        title,
        description,
        projectId,
        severity,
        status,
        amount,
        impactDays,
        author: history[0].person,
        submittedBy,
        sentForApproval,
        createdAt: time,
        source: "demo",
        history,
      };
    },
  );
}

export const money = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value);
export const shortDate = (value: string) =>
  new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "America/Los_Angeles",
  }).format(new Date(value));
export const getProject = (id: string) =>
  projects.find((project) => project.id === id) ?? projects[0];
export const statusLabels: Record<ChangeStatus, string> = {
  submitted: "Submitted",
  in_review: "In review",
  authorized_to_proceed: "Work authorized · estimate pending",
  withdrawn: "Withdrawn",
  awaiting_gc: "Awaiting approval",
  approved: "Approved",
  declined: "Declined",
};
