import { ArrowUpRight, Building2, MapPin, Plus } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { useWorkspace } from "./context";
import { isSubmitterRole, money, projects } from "./data";
import { AppShell, go } from "./shell";
import {
  Avatar,
  Button,
  Card,
  EmptyState,
  PageHeading,
  ProjectArt,
} from "./ui";

export function ProjectsScreen() {
  const { changes, role } = useWorkspace();
  if (role === "approver") {
    return (
      <AppShell title="Approver workspace">
        <Card>
          <EmptyState
            title="Review proposals in your decision queue"
            description="Open the queue to see the changes shared with you for a decision."
            action="Open decision queue"
            onAction={() => go("/requests")}
          />
        </Card>
      </AppShell>
    );
  }

  const isSubcontractor = role === "subcontractor";
  const isOffice = role === "office";
  const title = isSubcontractor ? "Job sites" : "Projects";
  const description = isSubcontractor
    ? "Find a job site and track your submitted changes."
    : isOffice
      ? "See which projects have requests waiting for office review."
      : "Track project progress and open change requests across your team.";
  return (
    <AppShell title={title}>
      <PageHeading
        title={title}
        description={description}
        action={
          isSubmitterRole(role) && (
            <Button icon={Plus} onPress={() => go("/new")}>
              {isSubcontractor ? "Report site change" : "New change request"}
            </Button>
          )
        }
      />
      <View className="mb-6 flex-row items-center gap-2">
        <View className="h-2 w-2 rounded-full bg-forest" />
        <Text className="text-[12px] font-semibold text-ink">
          {projects.length}{" "}
          {isSubcontractor ? "active sites" : "active projects"}
        </Text>
        <Text className="ml-auto text-[10px] text-muted">
          Sample project workspace
        </Text>
      </View>
      {!isSubcontractor && (
        <View className="mb-5 gap-2">
          <Text className="text-[13px] font-semibold text-ink">
            Project work orders
          </Text>
          {projects.map((project) => (
            <Button
              key={project.id}
              variant="secondary"
              onPress={() => go("/work-order?project=" + project.id)}
            >
              {project.name + " work order"}
            </Button>
          ))}
        </View>
      )}
      <View className="flex-row flex-wrap gap-5">
        {projects.map((project, i) => {
          const requests = changes.filter(
            (change) => change.projectId === project.id,
          );
          const open = requests.filter(({ status }) =>
            isOffice
              ? status === "submitted"
              : status === "submitted" || status === "awaiting_gc",
          ).length;
          return (
            <Pressable
              key={project.id}
              accessibilityRole="button"
              accessibilityLabel={`Open ${isSubcontractor ? "job site" : "project"}: ${project.name}`}
              onPress={() =>
                go("/requests?project=" + encodeURIComponent(project.id))
              }
              className="w-full overflow-hidden rounded-card border border-line bg-white hover:border-[#A9C0AA] sm:min-w-[270px] sm:flex-1"
            >
              <ProjectArt height={180} variant={i} />
              <View className="gap-4 p-5">
                <View className="flex-row items-center justify-between">
                  <View className="rounded-full bg-mint px-2.5 py-1">
                    <Text className="text-[9px] font-semibold text-forest">
                      {isSubcontractor ? "ACTIVE SITE" : "ACTIVE PROJECT"}
                    </Text>
                  </View>
                  <ArrowUpRight size={17} color="#74827C" />
                </View>
                <View>
                  <Text className="text-[18px] font-semibold tracking-[-0.4px] text-ink">
                    {project.name}
                  </Text>
                  <View className="mt-2 flex-row items-center gap-1">
                    <MapPin size={12} color="#8B9B90" />
                    <Text className="text-[10px] text-muted">
                      {project.address}
                    </Text>
                  </View>
                </View>
                {!isSubcontractor && (
                  <>
                    <View className="flex-row justify-between">
                      <Text className="text-[10px] text-muted">
                        Project progress
                      </Text>
                      <Text className="text-[10px] font-semibold text-forest">
                        {project.progress}%
                      </Text>
                    </View>
                    <View className="-mt-2 h-1.5 overflow-hidden rounded-full bg-canvas">
                      <View
                        className="h-full rounded-full bg-[#7C9D73]"
                        style={{ width: `${project.progress}%` }}
                      />
                    </View>
                  </>
                )}
                <View className="flex-row justify-between gap-3 border-b border-line pb-4">
                  {!isSubcontractor && (
                    <View>
                      <Text className="text-[9px] text-muted">
                        Project budget
                      </Text>
                      <Text className="mt-1 text-[13px] font-semibold text-ink">
                        {money(project.budget)}
                      </Text>
                    </View>
                  )}
                  <View className={isSubcontractor ? "" : "items-end"}>
                    <Text className="text-[9px] text-muted">
                      {isSubcontractor ? "Your submissions" : "Change requests"}
                    </Text>
                    <Text className="mt-1 text-[13px] font-semibold text-ink">
                      {requests.length}{" "}
                      <Text className="text-[10px] font-normal text-muted">
                        · {open} {isOffice ? "to review" : "open"}
                      </Text>
                    </Text>
                  </View>
                </View>
                {!isSubcontractor && (
                  <View className="flex-row items-center gap-2">
                    <Avatar name={project.client} size={27} />
                    <Text className="flex-1 text-[10px] text-muted">
                      {project.client}
                    </Text>
                    <Building2 size={15} color="#99AA9C" />
                  </View>
                )}
              </View>
            </Pressable>
          );
        })}
      </View>
    </AppShell>
  );
}
