import { type Href, router, usePathname } from "expo-router";
import {
  Activity,
  ArrowUpRight,
  Bell,
  Building2,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  HelpCircle,
  LayoutDashboard,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  X,
} from "lucide-react-native";
import { type ReactNode, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useWorkspace } from "./context";
import { roles, type Role } from "./data";
import { Avatar, Button, Card } from "./ui";

export const go = (path: string) => router.push(path as Href);
export const openChange = (id: string) =>
  go("/changes/" + encodeURIComponent(id));
const navigation = [
  { path: "/", title: "Overview", icon: LayoutDashboard },
  { path: "/requests", title: "Change requests", icon: ClipboardList },
  { path: "/projects", title: "Projects", icon: Building2 },
  { path: "/activity", title: "Activity", icon: Activity },
];

export function AppShell({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  const insets = useSafeAreaInsets();
  const pathname = usePathname();
  const { role, setRole, mode, unread, changes } = useWorkspace();
  const [panel, setPanel] = useState<"role" | "help" | null>(null);
  const [search, setSearch] = useState("");
  const profile = roles[role];
  const pending = changes.filter(
    (change) =>
      change.status === "submitted" || change.status === "awaiting_client",
  ).length;

  return (
    <View
      className="flex-1 flex-row bg-canvas"
      style={{ paddingTop: insets.top }}
    >
      <View className="hidden w-[228px] bg-sidebar px-4 pb-5 pt-8 lg:flex">
        <View className="mb-10 flex-row items-center gap-2.5 px-3">
          <BrandMark />
          <Text className="text-[19px] font-semibold tracking-[-0.7px] text-white">
            ChangeOrder<Text className="text-[#93BAA0]">.</Text>
          </Text>
        </View>
        <View className="mb-7 flex-row items-center gap-3 rounded-xl border border-[#345044] bg-[#203E31] px-3 py-3">
          <View className="h-8 w-8 items-center justify-center rounded-lg bg-[#385640]">
            <Building2 size={16} color="#DAE9D8" />
          </View>
          <View className="flex-1">
            <Text className="text-[12px] font-semibold text-white">
              Aven Construction
            </Text>
            <Text className="mt-1 text-[10px] text-[#A5B8AB]">
              Team workspace
            </Text>
          </View>
        </View>
        <Text className="mb-3 px-3 text-[9px] font-semibold tracking-[2px] text-[#83A18F]">
          WORKSPACE
        </Text>
        <View className="gap-1.5">
          {navigation.map((item) => {
            const active =
              item.path === "/"
                ? pathname === "/"
                : pathname.startsWith(item.path);
            return (
              <Pressable
                key={item.path}
                accessibilityRole="button"
                accessibilityLabel={item.title}
                onPress={() => go(item.path)}
                className={`min-h-[44px] flex-row items-center gap-3 rounded-xl px-3 ${active ? "bg-[#2B4D3C]" : "hover:bg-[#203E31]"}`}
              >
                <item.icon
                  size={17}
                  color={active ? "#E4F3DE" : "#A6BCAD"}
                  strokeWidth={1.7}
                />
                <Text
                  className={`flex-1 text-[12px] ${active ? "font-semibold text-white" : "text-[#B4C6B9]"}`}
                >
                  {item.title}
                </Text>
                {item.path === "/requests" && (
                  <View className="rounded-md bg-[#3B5A45] px-1.5 py-0.5">
                    <Text className="text-[9px] font-semibold text-[#D3E5CD]">
                      {pending}
                    </Text>
                  </View>
                )}
              </Pressable>
            );
          })}
        </View>
        <View className="mt-auto gap-4">
          <View className="rounded-2xl border border-[#345044] bg-[#1C392D] p-4">
            <View className="mb-3 h-8 w-8 items-center justify-center rounded-lg bg-[#385640]">
              <ShieldCheck size={17} color="#C4D8AD" />
            </View>
            <Text className="text-[12px] font-semibold text-[#E4EFDF]">
              From field to final approval.
            </Text>
            <Text className="mb-3 mt-2 text-[10px] leading-[17px] text-[#A3B7A7]">
              Walk through the workflow by switching your preview role.
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => setPanel("help")}
              className="flex-row items-center gap-2 py-1"
            >
              <Text className="text-[10px] font-semibold text-[#C9DABD]">
                Explore the demo
              </Text>
              <ArrowUpRight size={12} color="#C9DABD" />
            </Pressable>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Settings"
            onPress={() => go("/settings")}
            className="flex-row items-center gap-3 rounded-xl px-3 py-3 hover:bg-[#203E31]"
          >
            <Settings2 size={17} color="#A6BCAD" />
            <Text className="text-[12px] text-[#B4C6B9]">Settings</Text>
          </Pressable>
          <View className="border-t border-[#345044] pt-4">
            <View className="flex-row items-center gap-3 px-2">
              <Avatar name={profile.person} />
              <View className="flex-1">
                <Text className="text-[11px] font-semibold text-white">
                  {profile.person}
                </Text>
                <Text className="mt-1 text-[9px] text-[#9CB1A2]">
                  {profile.label}
                </Text>
              </View>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Help with demo"
                onPress={() => setPanel("help")}
              >
                <HelpCircle size={16} color="#8BA592" />
              </Pressable>
            </View>
          </View>
        </View>
      </View>

      <View className="min-w-0 flex-1">
        <View className="min-h-[72px] flex-row items-center justify-between gap-3 border-b border-line bg-white px-5 lg:px-8">
          <View className="hidden flex-row items-center gap-2 lg:flex">
            <Text className="text-[11px] text-muted">Workspace</Text>
            <ChevronRight size={12} color="#A5B0A7" />
            <Text className="text-[11px] font-semibold text-ink">{title}</Text>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Overview"
            onPress={() => go("/")}
            className="flex-row items-center gap-2 lg:hidden"
          >
            <BrandMark small />
            <Text className="text-[15px] font-bold tracking-[-0.5px] text-ink">
              ChangeOrder.
            </Text>
          </Pressable>
          <View className="flex-row items-center gap-3 lg:gap-5">
            <View className="hidden w-[190px] flex-row items-center gap-2 xl:flex">
              <Search size={15} color="#8D9B91" />
              <TextInput
                accessibilityLabel="Search all requests"
                value={search}
                onChangeText={setSearch}
                onSubmitEditing={() =>
                  go("/requests?search=" + encodeURIComponent(search))
                }
                placeholder="Search requests..."
                placeholderTextColor="#8D9B91"
                className="min-h-[40px] flex-1 text-[11px] text-ink"
              />
            </View>
            <Pressable
              accessibilityRole="button"
              onPress={() => go("/settings")}
              className="hidden rounded-md border border-line px-2 py-1 lg:flex"
            >
              <Text className="text-[9px] font-semibold text-muted">
                {mode === "demo" ? "DEMO WORKSPACE" : "CONNECTED MODE"}
              </Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Preview role"
              onPress={() => setPanel("role")}
              className="min-h-[40px] flex-row items-center gap-2 rounded-lg bg-canvas px-2.5"
            >
              <Text className="text-[10px] font-semibold text-ink">
                {role === "office"
                  ? "Office"
                  : role === "field"
                    ? "Field"
                    : "Client"}{" "}
                preview
              </Text>
              <ChevronDown size={12} color="#74827C" />
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Notifications"
              onPress={() => go("/activity")}
              className="relative min-h-[40px] min-w-[28px] items-center justify-center"
            >
              <Bell size={19} color="#64766A" strokeWidth={1.6} />
              {unread > 0 && (
                <View className="absolute right-1 top-2 h-1.5 w-1.5 rounded-full border border-white bg-orange-400" />
              )}
            </Pressable>
          </View>
        </View>

        <ScrollView
          className="flex-1"
          keyboardShouldPersistTaps="handled"
          automaticallyAdjustKeyboardInsets
          keyboardDismissMode="on-drag"
          contentContainerStyle={{
            paddingBottom: 20 + insets.bottom,
          }}
        >
          <View className="mx-auto w-full max-w-[1480px] px-5 pb-28 pt-7 lg:px-8 lg:pb-4 lg:pt-8">
            {children}
          </View>
        </ScrollView>

        <View
          className="absolute bottom-0 left-0 right-0 flex-row border-t border-line bg-white px-1 pt-2 lg:hidden"
          style={{ paddingBottom: Math.max(insets.bottom, 12) }}
        >
          {navigation.map((item) => {
            const active =
              item.path === "/"
                ? pathname === "/"
                : pathname.startsWith(item.path);
            return (
              <Pressable
                key={item.path}
                accessibilityRole="button"
                accessibilityLabel={item.title}
                onPress={() => go(item.path)}
                className="min-h-[48px] flex-1 items-center gap-1.5"
              >
                <item.icon
                  size={19}
                  color={active ? "#23664D" : "#8B9B90"}
                  strokeWidth={active ? 2 : 1.6}
                />
                <Text
                  className={`text-[9px] ${active ? "font-semibold text-forest" : "text-muted"}`}
                >
                  {item.path === "/requests" ? "Requests" : item.title}
                </Text>
              </Pressable>
            );
          })}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Settings"
            onPress={() => go("/settings")}
            className="min-h-[48px] flex-1 items-center gap-1.5"
          >
            <Settings2 size={19} color="#8B9B90" />
            <Text className="text-[9px] text-muted">Settings</Text>
          </Pressable>
        </View>
      </View>

      <Modal
        visible={panel !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setPanel(null)}
      >
        <View className="flex-1 items-center justify-center px-5">
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close dialog"
            className="absolute inset-0 bg-black/35"
            onPress={() => setPanel(null)}
          />
          <Card className="w-full max-w-[420px] p-6">
            <View className="mb-2 flex-row items-center justify-between">
              <Text className="text-[20px] font-bold text-ink">
                {panel === "role"
                  ? "See every side of a change."
                  : "One change. Three perspectives."}
              </Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Close"
                onPress={() => setPanel(null)}
                className="p-1"
              >
                <X size={18} color="#74827C" />
              </Pressable>
            </View>
            <Text className="mb-5 text-[12px] leading-5 text-muted">
              {panel === "role"
                ? "Switch preview roles to demonstrate the workflow. This is a local preview, not account authentication."
                : "Create a request as Field, review it as Office, then approve or decline it as Client. Demo requests stay in this workspace."}
            </Text>
            <View className="gap-2">
              {(Object.keys(roles) as Role[]).map((key) => (
                <Pressable
                  key={key}
                  accessibilityRole="button"
                  accessibilityLabel={"Preview as " + roles[key].label}
                  onPress={() => {
                    setRole(key);
                    setPanel(null);
                  }}
                  className={`flex-row items-center gap-3 rounded-xl border p-3 ${role === key ? "border-forest bg-mint" : "border-line bg-white"}`}
                >
                  <Avatar name={roles[key].person} size={36} />
                  <View className="flex-1">
                    <Text className="text-[12px] font-semibold text-ink">
                      {roles[key].label}
                    </Text>
                    <Text className="mt-1 text-[10px] text-muted">
                      {roles[key].caption}
                    </Text>
                  </View>
                  <ChevronRight size={15} color="#74827C" />
                </Pressable>
              ))}
            </View>
            <View className="mt-4">
              <Button
                variant="quiet"
                onPress={() => {
                  setPanel(null);
                  go("/new");
                }}
                icon={Plus}
              >
                Create a change request
              </Button>
            </View>
          </Card>
        </View>
      </Modal>
    </View>
  );
}

function BrandMark({ small }: { small?: boolean }) {
  return (
    <View
      className={`${small ? "h-7 w-7" : "h-8 w-8"} items-center justify-center rounded-lg bg-[#C4D5AB]`}
    >
      <View className="flex-row gap-0.5">
        <View className="h-3.5 w-1.5 rounded-sm bg-[#254A33]" />
        <View
          className="h-3.5 w-1.5 rounded-sm bg-[#254A33]"
          style={{ transform: [{ translateY: -3 }] }}
        />
      </View>
    </View>
  );
}
