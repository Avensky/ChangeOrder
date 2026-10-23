import { ArrowUpRight, Building2, MapPin, Plus } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { useWorkspace } from "./context";
import { money, projects } from "./data";
import { AppShell, go } from "./shell";
import { Avatar, Button, PageHeading, ProjectArt } from "./ui";

export function ProjectsScreen() {
  const { changes } = useWorkspace();
  return (
    <AppShell title="Projects">
      <PageHeading
        eyebrow="THE BIG PICTURE, DOWN TO THE DETAILS"
        title="Projects"
        description="Every change belongs to a bigger plan. Keep yours in view."
        action={
          <Button icon={Plus} onPress={() => go("/new")}>
            New change request
          </Button>
        }
      />
      <View className="mb-6 flex-row items-center gap-2">
        <View className="h-2 w-2 rounded-full bg-forest" />
        <Text className="text-[12px] font-semibold text-ink">
          3 active projects
        </Text>
        <Text className="ml-auto text-[10px] text-muted">
          Sample project workspace
        </Text>
      </View>
      <View className="flex-row flex-wrap gap-5">
        {projects.map((project, i) => {
          const requests = changes.filter(
            (change) => change.projectId === project.id,
          );
          const open = requests.filter(
            (change) =>
              change.status === "submitted" ||
              change.status === "awaiting_client",
          ).length;
          return (
            <Pressable
              key={project.id}
              accessibilityRole="button"
              accessibilityLabel={"Open project: " + project.name}
              onPress={() => go("/requests?project=" + project.id)}
              className="min-w-[270px] flex-1 overflow-hidden rounded-card border border-line bg-white hover:border-[#A9C0AA]"
            >
              <ProjectArt height={180} variant={i} />
              <View className="gap-4 p-5">
                <View className="flex-row items-center justify-between">
                  <View className="rounded-full bg-mint px-2.5 py-1">
                    <Text className="text-[9px] font-semibold text-forest">
                      ACTIVE PROJECT
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
                <View className="flex-row justify-between border-b border-line pb-4">
                  <View>
                    <Text className="text-[9px] text-muted">
                      Project budget
                    </Text>
                    <Text className="mt-1 text-[13px] font-semibold text-ink">
                      {money(project.budget)}
                    </Text>
                  </View>
                  <View className="items-end">
                    <Text className="text-[9px] text-muted">
                      Change requests
                    </Text>
                    <Text className="mt-1 text-[13px] font-semibold text-ink">
                      {requests.length}{" "}
                      <Text className="text-[10px] font-normal text-muted">
                        · {open} open
                      </Text>
                    </Text>
                  </View>
                </View>
                <View className="flex-row items-center gap-2">
                  <Avatar name={project.client} size={27} />
                  <Text className="flex-1 text-[10px] text-muted">
                    {project.client}
                  </Text>
                  <Building2 size={15} color="#99AA9C" />
                </View>
              </View>
            </Pressable>
          );
        })}
      </View>
    </AppShell>
  );
}
