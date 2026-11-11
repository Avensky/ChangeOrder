import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  FileText,
  Plus,
  Wallet,
} from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { useWorkspace } from "./context";
import { getProject, money, roles, shortDate } from "./data";
import { AppShell, go, openChange } from "./shell";
import {
  Avatar,
  Button,
  Card,
  ProjectArt,
  RequestRow,
  SectionTitle,
} from "./ui";

export function OverviewScreen() {
  const { changes, events, role } = useWorkspace();
  const office = changes.filter((change) => change.status === "submitted");
  const client = changes.filter(
    (change) => change.status === "awaiting_client",
  );
  const approved = changes.filter((change) => change.status === "approved");
  const stats = [
    {
      label: "Open requests",
      value: String(office.length + client.length).padStart(2, "0"),
      note: "Across your active projects",
      icon: FileText,
      color: "#658476",
      bg: "bg-mint",
    },
    {
      label: "Awaiting approval",
      value: String(client.length).padStart(2, "0"),
      note: "Ready for a client decision",
      icon: Clock3,
      color: "#AD7F3B",
      bg: "bg-amber-50",
    },
    {
      label: "Approved changes",
      value: String(approved.length).padStart(2, "0"),
      note: "Cleared to move forward",
      icon: CheckCircle2,
      color: "#5A8B72",
      bg: "bg-emerald-50",
    },
    {
      label: "Approved value",
      value: money(approved.reduce((sum, change) => sum + change.amount, 0)),
      note: "Total approved change value",
      icon: Wallet,
      color: "#7A8194",
      bg: "bg-slate-100",
    },
  ];
  const next = role === "client" ? client[0] : office[0];

  return (
    <AppShell title="Overview">
      <View className="mb-6 gap-4 lg:flex-row lg:items-center lg:justify-between">
        <View className="min-w-0 lg:flex-1">
          <Text className="mb-2 text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
            YOUR PROJECT WORKSPACE
          </Text>
          <Text
            accessibilityRole="header"
            className="text-[28px] font-bold leading-9 tracking-[-0.8px] text-ink"
          >
            Everything moving forward.
          </Text>
          <Text className="mt-2 text-[13px] text-muted">
            A clear view of every change, from the field to approval.
          </Text>
        </View>
        <Button onPress={() => go("/new")} icon={Plus}>
          New change request
        </Button>
      </View>

      <View className="mb-6 overflow-hidden rounded-card border border-[#DDE7D6] bg-[#ECF2E6]">
        <View className="flex-row items-center">
          <View className="flex-1 gap-3 p-6 lg:p-7">
            <View className="self-start flex-row items-center gap-1.5 rounded-full border border-[#D5E2CC] bg-[#F8FAF4] px-2 py-1">
              <View className="h-1.5 w-1.5 rounded-full bg-forest" />
              <Text className="text-[9px] font-semibold text-forest">
                BUILT FOR THE WAY YOU WORK
              </Text>
            </View>
            <Text className="max-w-[430px] text-[23px] font-semibold leading-8 tracking-[-0.6px] text-ink">
              Less waiting. More building.
            </Text>
            <Text className="max-w-[390px] text-[12px] leading-5 text-[#72816C]">
              Capture changes on site, keep the office in the loop, and give
              clients a simple way to say yes.
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => go("/new")}
              className="mt-1 flex-row items-center gap-2 self-start py-1"
            >
              <Text className="text-[11px] font-semibold text-forest">
                Capture a change
              </Text>
              <ArrowRight size={14} color="#23664D" />
            </Pressable>
          </View>
          <View className="hidden w-[290px] lg:flex">
            <ProjectArt height={218} />
          </View>
        </View>
      </View>

      <View className="mb-6 flex-row flex-wrap gap-3 lg:gap-4">
        {stats.map((stat) => (
          <Card
            key={stat.label}
            className="min-w-[145px] flex-1 p-4 lg:min-w-[180px] lg:p-5"
          >
            <View className="mb-5 flex-row items-center justify-between">
              <Text className="flex-1 text-[11px] font-medium text-muted">
                {stat.label}
              </Text>
              <View
                className={`h-8 w-8 items-center justify-center rounded-lg ${stat.bg}`}
              >
                <stat.icon size={16} color={stat.color} strokeWidth={1.7} />
              </View>
            </View>
            <Text className="text-[28px] font-semibold tracking-[-1px] text-ink">
              {stat.value}
            </Text>
            <Text className="mt-2 text-[10px] text-muted">{stat.note}</Text>
          </Card>
        ))}
      </View>

      <View className="flex-col gap-6 xl:flex-row">
        <View className="min-w-0 flex-1 gap-6">
          <Card className="overflow-hidden">
            <View className="px-5 pt-5">
              <SectionTitle
                title="Recent change requests"
                action="View all requests"
                onAction={() => go("/requests")}
              />
              <View className="mb-3 hidden flex-row md:flex">
                <Text className="flex-1 pl-[52px] text-[9px] font-semibold uppercase tracking-wider text-muted">
                  Request / Project
                </Text>
                <Text className="w-[138px] text-[9px] font-semibold uppercase tracking-wider text-muted">
                  Status
                </Text>
                <Text className="hidden w-[100px] text-[9px] font-semibold uppercase tracking-wider text-muted xl:flex">
                  Priority
                </Text>
                <Text className="w-[78px] text-right text-[9px] font-semibold uppercase tracking-wider text-muted">
                  Value
                </Text>
                <View className="w-6" />
              </View>
            </View>
            {changes.slice(0, 5).map((change) => (
              <RequestRow
                key={change.id}
                change={change}
                onPress={() => openChange(change.id)}
              />
            ))}
          </Card>
          <View>
            <View className="mb-4 flex-row items-center justify-between">
              <Text className="text-[15px] font-semibold text-ink">
                Your active projects
              </Text>
              <Pressable
                accessibilityRole="button"
                onPress={() => go("/projects")}
                className="flex-row items-center gap-1 py-2"
              >
                <Text className="text-[11px] font-semibold text-forest">
                  View projects
                </Text>
                <ArrowUpRight size={13} color="#23664D" />
              </Pressable>
            </View>
            <View className="flex-row flex-wrap gap-3">
              {["north-park", "harbor", "cedar"].map((id) => {
                const project = getProject(id);
                return (
                  <Pressable
                    key={id}
                    accessibilityRole="button"
                    onPress={() => go("/requests?project=" + id)}
                    className="min-w-[160px] flex-1 rounded-2xl border border-line bg-white p-4 hover:border-[#B8CDBE]"
                  >
                    <View
                      className="mb-3 h-9 w-9 items-center justify-center rounded-xl"
                      style={{ backgroundColor: project.color }}
                    >
                      <Text className="text-[10px] font-bold text-forest">
                        {project.initials}
                      </Text>
                    </View>
                    <Text className="text-[12px] font-semibold text-ink">
                      {project.name}
                    </Text>
                    <Text className="mt-1 text-[10px] text-muted">
                      {project.progress}% complete
                    </Text>
                    <View className="mt-3 h-1 overflow-hidden rounded-full bg-canvas">
                      <View
                        className="h-full rounded-full bg-[#83A27D]"
                        style={{ width: `${project.progress}%` }}
                      />
                    </View>
                  </Pressable>
                );
              })}
            </View>
          </View>
        </View>

        <View className="w-full gap-5 xl:w-[292px]">
          <Card className="p-5">
            <SectionTitle title="Needs your attention" />
            <View className="mb-4 h-10 w-10 items-center justify-center rounded-xl bg-sand">
              <Clock3 size={20} color="#A77B43" strokeWidth={1.5} />
            </View>
            <Text className="text-[17px] font-semibold leading-6 text-ink">
              {role === "client"
                ? `${client.length} requests ready for your decision`
                : `${office.length} changes ready for office review`}
            </Text>
            <Text className="mb-4 mt-2 text-[11px] leading-[18px] text-muted">
              {next
                ? next.title + " is next in the queue."
                : "You’re all caught up. New requests will appear here."}
            </Text>
            <Button
              variant="secondary"
              onPress={() => (next ? openChange(next.id) : go("/requests"))}
              icon={ArrowRight}
            >
              Review next request
            </Button>
          </Card>
          <Card className="p-5">
            <SectionTitle
              title="Latest activity"
              action="All activity"
              onAction={() => go("/activity")}
            />
            <View className="gap-5">
              {events.slice(0, 4).map((event) => (
                <Pressable
                  key={event.id}
                  accessibilityRole="button"
                  onPress={() => openChange(event.changeId)}
                  className="flex-row gap-3"
                >
                  <Avatar name={event.person} size={28} />
                  <View className="flex-1">
                    <Text className="text-[11px] leading-[17px] text-ink">
                      {event.title}
                    </Text>
                    <Text className="mt-1 text-[9px] text-muted">
                      {event.person.split(" ")[0]} · {shortDate(event.time)}
                    </Text>
                  </View>
                </Pressable>
              ))}
            </View>
          </Card>
          <View className="px-2">
            <Text className="text-[10px] leading-[17px] text-muted">
              Previewing as{" "}
              <Text className="font-semibold text-forest">
                {roles[role].label}
              </Text>
              . Switch roles in the top bar to explore the workflow.
            </Text>
          </View>
        </View>
      </View>
    </AppShell>
  );
}
