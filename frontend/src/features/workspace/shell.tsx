import { type Href, router, usePathname } from "expo-router";
import {
  Activity,
  Bell,
  Building2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  LayoutDashboard,
  Plus,
  Search,
  Settings2,
  type LucideIcon,
} from "lucide-react-native";
import { type ReactNode, useState } from "react";
import {
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useSession } from "@/features/auth/session";
import { useWorkspace } from "./context";
import { roles, type Role } from "./data";
import { Avatar } from "./ui";

export const go = (path: string) => router.push(path as Href);
export const openChange = (id: string) =>
  go("/changes/" + encodeURIComponent(id));
const navigationIcons = {
  "/": LayoutDashboard,
  "/requests": ClipboardList,
  "/projects": Building2,
  "/activity": Activity,
};

type NavigationItem = readonly [
  path: keyof typeof navigationIcons,
  title: string,
  mobileTitle: string,
];

const roleNavigation: Record<
  Role,
  {
    links: readonly NavigationItem[];
    action: { path: string; title: string; icon: LucideIcon };
  }
> = {
  manager: {
    links: [["/", "Manager overview", "Overview"], ["/requests", "Work authorizations", "Requests"], ["/activity", "Team activity", "Activity"]],
    action: { path: "/requests?high=1", title: "Review urgent work", icon: ClipboardCheck },
  },
  contractor: {
    links: [
      ["/", "Job overview", "Overview"],
      ["/requests", "Team requests", "Requests"],
      ["/projects", "Projects", "Projects"],
      ["/activity", "Team activity", "Activity"],
    ],
    action: { path: "/new", title: "New change request", icon: Plus },
  },
  subcontractor: {
    links: [
      ["/", "Field overview", "Field"],
      ["/requests", "My submissions", "My requests"],
      ["/projects", "Job sites", "Sites"],
      ["/activity", "My updates", "Updates"],
    ],
    action: { path: "/new", title: "Report site change", icon: Plus },
  },
  office: {
    links: [
      ["/", "Operations", "Office"],
      ["/requests", "Review queue", "Review"],
      ["/projects", "Projects", "Projects"],
      ["/activity", "Review activity", "Activity"],
    ],
    action: {
      path: "/requests?status=submitted",
      title: "Review submissions",
      icon: ClipboardCheck,
    },
  },
  approver: {
    links: [
      ["/", "Approvals", "Overview"],
      ["/requests", "Decision queue", "Decisions"],
      ["/activity", "Decision activity", "Activity"],
    ],
    action: {
      path: "/requests?status=awaiting_client",
      title: "Review proposals",
      icon: ClipboardCheck,
    },
  },
};

function isActiveRoute(pathname: string, path: NavigationItem[0]) {
  return (
    pathname === path ||
    (path === "/requests" && pathname.startsWith("/changes/"))
  );
}

export function AppShell({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  const insets = useSafeAreaInsets();
  const pathname = usePathname();
  const { role, mode, unread, changes, syncError, refresh } =
    useWorkspace();
  const [search, setSearch] = useState("");
  const { user } = useSession();
  const profile = { ...roles[role], person: user?.name ?? roles[role].person };
  const { links, action } = roleNavigation[role];
  const pending = changes.filter(({ status }) => {
    if (role === "office") return ["submitted", "in_review", "authorized_to_proceed"].includes(status);
    if (role === "approver") return status === "awaiting_gc";
    return status === "submitted" || status === "awaiting_gc";
  }).length;

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
              {profile.label} workspace
            </Text>
          </View>
        </View>
        <Text className="mb-3 px-3 text-[9px] font-semibold tracking-[2px] text-[#83A18F]">
          WORKSPACE
        </Text>
        <View className="gap-1.5">
          {links.map(([path, label]) => {
            const active = isActiveRoute(pathname, path);
            const Icon = navigationIcons[path];
            return (
              <Pressable
                key={path}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected: active }}
                onPress={() => go(path)}
                className={`min-h-[44px] flex-row items-center gap-3 rounded-xl px-3 ${active ? "bg-[#2B4D3C]" : "hover:bg-[#203E31]"}`}
              >
                <Icon
                  size={17}
                  color={active ? "#E4F3DE" : "#A6BCAD"}
                  strokeWidth={1.7}
                />
                <Text
                  className={`flex-1 text-[12px] ${active ? "font-semibold text-white" : "text-[#B4C6B9]"}`}
                >
                  {label}
                </Text>
                {path === "/requests" && pending > 0 && (
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
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={action.title}
            onPress={() => go(action.path)}
            className="min-h-[44px] flex-row items-center gap-2.5 rounded-xl bg-[#C4D5AB] px-3 hover:bg-[#D4E1C4] active:opacity-80"
          >
            <action.icon size={17} color="#254A33" strokeWidth={1.8} />
            <Text className="text-[12px] font-semibold text-[#254A33]">
              {action.title}
            </Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Settings"
            accessibilityState={{ selected: pathname === "/settings" }}
            onPress={() => go("/settings")}
            className="flex-row items-center gap-3 rounded-xl px-3 py-3 hover:bg-[#203E31]"
          >
            <Settings2 size={17} color="#A6BCAD" />
            <Text className="text-[12px] text-[#B4C6B9]">Settings</Text>
          </Pressable>
          <View className="border-t border-[#345044] pt-4">
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Account settings"
              onPress={() => go("/settings")}
              className="min-h-[44px] flex-row items-center gap-3 rounded-xl px-2 hover:bg-[#203E31]"
            >
              <Avatar name={profile.person} />
              <View className="flex-1">
                <Text className="text-[11px] font-semibold text-white">
                  {profile.person}
                </Text>
                <Text className="mt-1 text-[9px] text-[#9CB1A2]">
                  {profile.label}
                </Text>
              </View>
              <ChevronDown size={14} color="#A5B8AB" />
            </Pressable>
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
            accessibilityLabel="Workspace home"
            onPress={() => go("/")}
            className="flex-row items-center gap-2 lg:hidden"
          >
            <BrandMark small />
            <Text className="hidden text-[15px] font-bold tracking-[-0.5px] text-ink sm:flex">
              ChangeOrder.
            </Text>
          </Pressable>
          <View className="flex-row items-center gap-3 lg:gap-5">
            <View className="hidden w-[190px] flex-row items-center gap-2 xl:flex">
              <Search size={15} color="#8D9B91" />
              <TextInput
                accessibilityLabel="Search workspace requests"
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
              accessibilityLabel="Signed-in account"
              onPress={() => go("/settings")}
              className="min-h-[44px] flex-row items-center gap-2 rounded-lg bg-canvas px-2.5"
            >
              <Text className="text-[10px] font-semibold text-ink">
                {profile.label}
              </Text>
              <ChevronDown size={12} color="#74827C" />
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Notifications"
              onPress={() => go("/activity")}
              className="relative min-h-[44px] min-w-[44px] items-center justify-center"
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
            {mode === "connected" && !!syncError && (
              <View className="mb-4 rounded-xl bg-red-50 p-4">
                <Text
                  accessibilityRole="alert"
                  className="mb-2 text-[12px] text-red-700"
                >
                  {syncError}
                </Text>
                <Pressable
                  accessibilityRole="button"
                  onPress={() => {
                    void refresh();
                  }}
                >
                  <Text className="font-semibold text-forest">
                    Retry refresh
                  </Text>
                </Pressable>
              </View>
            )}
            {children}
          </View>
        </ScrollView>

        <View
          className="absolute bottom-0 left-0 right-0 flex-row border-t border-line bg-white px-1 pt-2 lg:hidden"
          style={{ paddingBottom: Math.max(insets.bottom, 12) }}
        >
          {links.map(([path, label, mobileLabel]) => {
            const active = isActiveRoute(pathname, path);
            const Icon = navigationIcons[path];
            return (
              <Pressable
                key={path}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected: active }}
                onPress={() => go(path)}
                className="min-h-[48px] flex-1 items-center gap-1.5"
              >
                <Icon
                  size={19}
                  color={active ? "#23664D" : "#8B9B90"}
                  strokeWidth={active ? 2 : 1.6}
                />
                <Text
                  className={`text-[9px] ${active ? "font-semibold text-forest" : "text-muted"}`}
                >
                  {mobileLabel}
                </Text>
              </Pressable>
            );
          })}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Settings"
            accessibilityState={{ selected: pathname === "/settings" }}
            onPress={() => go("/settings")}
            className="min-h-[48px] flex-1 items-center gap-1.5"
          >
            <Settings2
              size={19}
              color={pathname === "/settings" ? "#23664D" : "#8B9B90"}
            />
            <Text
              className={`text-[9px] ${pathname === "/settings" ? "font-semibold text-forest" : "text-muted"}`}
            >
              Settings
            </Text>
          </Pressable>
        </View>
      </View>


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
