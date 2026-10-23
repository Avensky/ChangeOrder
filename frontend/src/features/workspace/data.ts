import type { ChangeOrder, Severity } from "@/features/change-orders/types";

export type Role = "field" | "office" | "client";
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
  impactDays: number;
  author: string;
  createdAt: string;
  source: Mode;
  photoUri?: string;
  history: Event[];
};

export const roles: Record<
  Role,
  { label: string; person: string; initials: string; caption: string }
> = {
  field: {
    label: "Field contractor",
    person: "Uriel Zacarias",
    initials: "UZ",
    caption: "Capture & submit",
  },
  office: {
    label: "Office coordinator",
    person: "Avery Morgan",
    initials: "AM",
    caption: "Review & coordinate",
  },
  client: {
    label: "Client / owner",
    person: "Jordan Ellis",
    initials: "JE",
    caption: "Approve & keep moving",
  },
};

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
    "awaiting_client",
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
    "awaiting_client",
    680,
    0,
  ],
  [
    "1042",
    "Custom kitchen shelving",
    "Add three floating oak shelves beside the range hood.",
    "north-park",
    "normal",
    "rejected",
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
      const history: Event[] = [
        {
          id: id + "-submitted",
          changeId: id,
          title: "Change request submitted",
          person: i % 2 ? "Marcus Rivera" : "Uriel Zacarias",
          time,
          kind: "submitted",
        },
      ];
      if (status !== "submitted")
        history.push({
          id: id + "-review",
          changeId: id,
          title:
            status === "awaiting_client"
              ? "Sent to client for approval"
              : "Office review completed",
          person: "Avery Morgan",
          time,
          kind: "review",
        });
      if (status === "approved" || status === "rejected")
        history.push({
          id: id + "-decision",
          changeId: id,
          title: status === "approved" ? "Change approved" : "Change declined",
          person: severity === "high" ? "Avery Morgan" : "Jordan Ellis",
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
    maximumFractionDigits: 0,
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
  submitted: "Office review",
  awaiting_client: "Awaiting approval",
  approved: "Approved",
  rejected: "Declined",
};
