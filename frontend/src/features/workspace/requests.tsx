import { router, useLocalSearchParams } from "expo-router";
import { Plus, Search, SlidersHorizontal, X } from "lucide-react-native";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { useWorkspace } from "./context";
import { type ChangeStatus, projects, statusLabels } from "./data";
import { AppShell, go, openChange } from "./shell";
import { Button, Card, EmptyState, PageHeading, RequestRow } from "./ui";

export function RequestsScreen() {
  const { changes } = useWorkspace();
  const params = useLocalSearchParams<{
    search?: string;
    status?: string;
    project?: string;
    high?: string;
  }>();
  const query = params.search ?? "";
  const status = params.status ?? "all";
  const items = changes.filter(
    (change) =>
      (status === "all" || change.status === status) &&
      (!params.project || change.projectId === params.project) &&
      (params.high !== "1" || change.severity === "high") &&
      (change.title + " " + change.description + " " + change.code)
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const filters: ("all" | ChangeStatus)[] = [
    "all",
    "submitted",
    "awaiting_client",
    "approved",
    "rejected",
  ];

  return (
    <AppShell title="Change requests">
      <PageHeading
        eyebrow="A CLEAR RECORD OF EVERY CHANGE"
        title="Change requests"
        description="Keep scope, cost, and approvals on the same page."
        action={
          <Button onPress={() => go("/new")} icon={Plus}>
            New change request
          </Button>
        }
      />
      <Card className="overflow-hidden">
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          className="border-b border-line"
        >
          <View className="flex-row gap-5 px-5">
            {filters.map((filter) => (
              <Pressable
                key={filter}
                accessibilityRole="button"
                accessibilityLabel={
                  "Filter: " +
                  (filter === "all" ? "All requests" : statusLabels[filter])
                }
                onPress={() => router.setParams({ status: filter })}
                className={`min-h-[56px] flex-row items-center gap-2 border-b-2 ${status === filter ? "border-forest" : "border-transparent"}`}
              >
                <Text
                  className={`text-[11px] ${status === filter ? "font-semibold text-forest" : "text-muted"}`}
                >
                  {filter === "all" ? "All requests" : statusLabels[filter]}
                </Text>
                <View
                  className={`rounded-md px-1.5 py-0.5 ${status === filter ? "bg-mint" : "bg-canvas"}`}
                >
                  <Text className="text-[9px] font-medium text-muted">
                    {filter === "all"
                      ? changes.length
                      : changes.filter((change) => change.status === filter)
                          .length}
                  </Text>
                </View>
              </Pressable>
            ))}
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
                onPress={() => router.setParams({ search: "" })}
              >
                <X size={13} color="#74827C" />
              </Pressable>
            )}
          </View>
          <Pressable
            accessibilityRole="button"
            onPress={() =>
              router.setParams({ high: params.high === "1" ? "" : "1" })
            }
            className={`min-h-[42px] flex-row items-center gap-2 rounded-xl border px-3 ${params.high === "1" ? "border-orange-300 bg-orange-50" : "border-line bg-white"}`}
          >
            <SlidersHorizontal size={14} color="#74827C" />
            <Text className="text-[11px] text-ink">High priority</Text>
          </Pressable>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          className="px-5"
        >
          <View className="mb-4 flex-row gap-2">
            <Pressable
              accessibilityRole="button"
              onPress={() => router.setParams({ project: "" })}
              className={`rounded-full px-3 py-2 ${!params.project ? "bg-mint" : "bg-canvas"}`}
            >
              <Text className="text-[10px] font-medium text-forest">
                All projects
              </Text>
            </Pressable>
            {projects.map((project) => (
              <Pressable
                key={project.id}
                accessibilityRole="button"
                onPress={() => router.setParams({ project: project.id })}
                className={`rounded-full px-3 py-2 ${params.project === project.id ? "bg-mint" : "bg-canvas"}`}
              >
                <Text className="text-[10px] text-forest">{project.name}</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>
        {items.length ? (
          items.map((change) => (
            <RequestRow
              key={change.id}
              change={change}
              onPress={() => openChange(change.id)}
            />
          ))
        ) : (
          <EmptyState
            title="No requests found"
            description="Try a different search or clear your filters to see more requests."
            onAction={() =>
              router.setParams({
                search: "",
                status: "all",
                high: "",
                project: "",
              })
            }
            action="Clear filters"
          />
        )}
        <View className="flex-row justify-between border-t border-line bg-[#FCFCFA] px-5 py-4">
          <Text className="text-[10px] text-muted">
            Showing {items.length} of {changes.length} requests
          </Text>
          <Text className="text-[10px] text-muted">
            Latest submissions first
          </Text>
        </View>
      </Card>
    </AppShell>
  );
}
