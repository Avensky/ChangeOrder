import { router, useLocalSearchParams } from "expo-router";
import { Plus, Search, SlidersHorizontal, X } from "lucide-react-native";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { useWorkspace } from "./context";
import {
  isSubmitterRole,
  projects,
  statusLabels,
  type ChangeStatus,
  type Role,
  type WorkspaceChange,
} from "./data";
import { AppShell, go, openChange } from "./shell";
import { Button, Card, EmptyState, PageHeading, RequestRow } from "./ui";

type QueueFilter = "all" | "decided" | ChangeStatus;

const allFilters: readonly QueueFilter[] = [
  "all",
  "submitted",
  "awaiting_client",
  "approved",
  "rejected",
];

const queues: Record<
  Role,
  {
    title: string;
    description: string;
    filters: readonly QueueFilter[];
    emptyTitle: string;
    emptyDescription: string;
    sortLabel: string;
  }
> = {
  contractor: {
    title: "Project requests",
    description:
      "Track changes across jobs and follow the status of field submissions.",
    filters: allFilters,
    emptyTitle: "No project requests",
    emptyDescription: "Requests submitted by the field team will appear here.",
    sortLabel: "Latest submissions first",
  },
  subcontractor: {
    title: "My submissions",
    description: "Follow the requests you sent from the field.",
    filters: allFilters,
    emptyTitle: "No submissions yet",
    emptyDescription: "Capture a site change to send it to the office for review.",
    sortLabel: "Latest submissions first",
  },
  office: {
    title: "Office review queue",
    description:
      "Work through incoming changes, starting with high-priority submissions.",
    filters: ["submitted", "all", "awaiting_client", "approved", "rejected"],
    emptyTitle: "No incoming requests",
    emptyDescription:
      "New submissions will appear here as the field team reports them.",
    sortLabel: "High-priority intake first",
  },
  approver: {
    title: "Approval queue",
    description:
      "Open a proposal to review its scope and terms. Use Decisions to see earlier outcomes.",
    filters: ["awaiting_client", "decided", "all"],
    emptyTitle: "No decisions waiting",
    emptyDescription:
      "New proposals will appear after the office sends them for approval.",
    sortLabel: "Decisions waiting first",
  },
};

function matchesStatus(change: WorkspaceChange, filter: QueueFilter) {
  if (filter === "all") return true;
  if (filter === "decided") {
    return change.status === "approved" || change.status === "rejected";
  }
  return change.status === filter;
}

function queueRank(change: WorkspaceChange, role: Role) {
  if (role === "office") {
    if (change.status !== "submitted") return 2;
    return change.severity === "high" ? 0 : 1;
  }
  if (role === "approver") return change.status === "awaiting_client" ? 0 : 1;
  return 0;
}

export function RequestsScreen() {
  const { changes, role } = useWorkspace();
  const params = useLocalSearchParams<{
    search?: string;
    status?: string;
    project?: string;
    high?: string;
  }>();
  const queue = queues[role];
  const query = typeof params.search === "string" ? params.search : "";
  const defaultFilter = queue.filters[0];
  const status =
    queue.filters.find((filter) => filter === params.status) ?? defaultFilter;
  const availableProjects =
    role === "approver"
      ? projects.filter((project) =>
          changes.some((change) => change.projectId === project.id),
        )
      : projects;
  const projectId = availableProjects.find(
    (project) => project.id === params.project,
  )?.id;
  const showPriorityFilter = role === "contractor" || role === "office";
  const highOnly = showPriorityFilter && params.high === "1";
  const search = query.trim().toLowerCase();
  const items = changes
    .filter(
      (change) =>
        matchesStatus(change, status) &&
        (!projectId || change.projectId === projectId) &&
        (!highOnly || change.severity === "high") &&
        (change.title + " " + change.description + " " + change.code)
          .toLowerCase()
          .includes(search),
    )
    .sort((a, b) => queueRank(a, role) - queueRank(b, role));
  const hasFilters = !!search || !!projectId || highOnly || status !== defaultFilter;

  return (
    <AppShell title={queue.title}>
      <PageHeading
        title={queue.title}
        description={queue.description}
        action={
          isSubmitterRole(role) ? (
            <Button onPress={() => go("/new")} icon={Plus}>
              {role === "subcontractor"
                ? "Capture a change"
                : "New change request"}
            </Button>
          ) : undefined
        }
      />
      <Card className="overflow-hidden">
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          className="border-b border-line"
        >
          <View className="flex-row gap-5 px-5">
            {queue.filters.map((filter) => {
              const label =
                filter === "all"
                  ? "All requests"
                  : filter === "decided"
                    ? "Decisions"
                    : statusLabels[filter];
              const selected = status === filter;
              return (
                <Pressable
                  key={filter}
                  accessibilityRole="button"
                  accessibilityLabel={"Filter: " + label}
                  accessibilityState={{ selected }}
                  onPress={() => router.setParams({ status: filter })}
                  className={`min-h-[56px] flex-row items-center gap-2 border-b-2 ${selected ? "border-forest" : "border-transparent"}`}
                >
                  <Text
                    className={`text-[11px] ${selected ? "font-semibold text-forest" : "text-muted"}`}
                  >
                    {label}
                  </Text>
                  <View className={`rounded-md px-1.5 py-0.5 ${selected ? "bg-mint" : "bg-canvas"}`}>
                    <Text className="text-[9px] font-medium text-muted">
                      {
                        changes.filter((change) => matchesStatus(change, filter))
                          .length
                      }
                    </Text>
                  </View>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>
        <View className="flex-row flex-wrap items-center gap-3 p-5">
          <View className="min-w-[180px] flex-1 flex-row items-center gap-2 rounded-xl border border-line bg-canvas px-3">
            <Search size={15} color="#8B9B90" />
            <TextInput
              accessibilityLabel="Search change requests"
              placeholder="Search by title, description, or reference"
              placeholderTextColor="#8B9B90"
              value={query}
              onChangeText={(value) => router.setParams({ search: value })}
              className="min-h-[42px] flex-1 text-[11px] text-ink"
            />
            {!!query && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Clear search"
                hitSlop={8}
                onPress={() => router.setParams({ search: "" })}
              >
                <X size={13} color="#74827C" />
              </Pressable>
            )}
          </View>
          {showPriorityFilter && (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: highOnly }}
              onPress={() => router.setParams({ high: highOnly ? "" : "1" })}
              className={`min-h-[42px] flex-row items-center gap-2 rounded-xl border px-3 ${highOnly ? "border-orange-300 bg-orange-50" : "border-line bg-white"}`}
            >
              <SlidersHorizontal size={14} color="#74827C" />
              <Text className="text-[11px] text-ink">High priority</Text>
            </Pressable>
          )}
        </View>
        {(availableProjects.length > 1 || projectId) && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            className="px-5"
          >
            <View className="mb-4 flex-row gap-2">
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: !projectId }}
                onPress={() => router.setParams({ project: "" })}
                className={`min-h-[36px] justify-center rounded-full px-3 py-2 ${!projectId ? "bg-mint" : "bg-canvas"}`}
              >
                <Text className="text-[10px] font-medium text-forest">
                  All projects
                </Text>
              </Pressable>
              {availableProjects.map((project) => (
                <Pressable
                  key={project.id}
                  accessibilityRole="button"
                  accessibilityState={{ selected: projectId === project.id }}
                  onPress={() => router.setParams({ project: project.id })}
                  className={`min-h-[36px] justify-center rounded-full px-3 py-2 ${projectId === project.id ? "bg-mint" : "bg-canvas"}`}
                >
                  <Text className="text-[10px] text-forest">
                    {project.name}
                  </Text>
                </Pressable>
              ))}
            </View>
          </ScrollView>
        )}
        {items.length ? (
          items.map((change) => (
            <RequestRow
              key={change.id}
              change={change}
              showAmount={role !== "subcontractor"}
              onPress={() => openChange(change.id)}
            />
          ))
        ) : (
          <EmptyState
            title={hasFilters ? "No requests found" : queue.emptyTitle}
            description={
              hasFilters
                ? "Try a different search or clear your filters."
                : queue.emptyDescription
            }
            onAction={
              hasFilters
                ? () =>
                    router.setParams({
                      search: "",
                      status: defaultFilter,
                      high: "",
                      project: "",
                    })
                : undefined
            }
            action="Clear filters"
          />
        )}
        <View className="flex-row flex-wrap justify-between gap-x-3 gap-y-1 border-t border-line bg-[#FCFCFA] px-5 py-4">
          <Text className="text-[10px] text-muted">
            Showing {items.length} of {changes.length} requests
          </Text>
          <Text className="text-[10px] text-muted">{queue.sortLabel}</Text>
        </View>
      </Card>
    </AppShell>
  );
}
