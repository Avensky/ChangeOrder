import {
  Check,
  Radio,
  RefreshCw,
  ShieldCheck,
  Wifi,
  X,
} from "lucide-react-native";
import { useState } from "react";
import { Modal, Pressable, Text, View } from "react-native";

import { API_URL, checkBackendHealth } from "@/lib/api";

import { useWorkspace } from "./context";
import { type Mode, type Role, roles } from "./data";
import { AppShell } from "./shell";
import { Avatar, Button, Card, PageHeading, SectionTitle } from "./ui";

export function SettingsScreen() {
  const { role, setRole, mode, setMode, reset } = useWorkspace();
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState("Not checked");
  const [confirm, setConfirm] = useState(false);
  async function check() {
    setChecking(true);
    try {
      await checkBackendHealth();
      setStatus("Backend: ok");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Connection failed");
    } finally {
      setChecking(false);
    }
  }

  return (
    <AppShell title="Settings">
      <PageHeading
        eyebrow="MAKE THE WORKSPACE YOURS"
        title="Workspace settings"
        description="Preview the people and steps behind a smooth approval."
      />
      <View className="flex-col gap-5 xl:flex-row">
        <View className="min-w-0 flex-1 gap-5">
          <Card className="p-5 lg:p-6">
            <SectionTitle title="Preview role" />
            <Text className="mb-5 text-[12px] leading-5 text-muted">
              Switch perspectives to demonstrate the work order workflow. These
              preview roles do not sign you into a real account.
            </Text>
            <View className="gap-3">
              {(Object.keys(roles) as Role[]).map((key) => (
                <Pressable
                  key={key}
                  accessibilityRole="radio"
                  accessibilityLabel={"Settings role: " + roles[key].label}
                  accessibilityState={{ checked: role === key }}
                  onPress={() => setRole(key)}
                  className={`flex-row items-center gap-3 rounded-xl border p-4 ${role === key ? "border-forest bg-mint" : "border-line"}`}
                >
                  <Avatar name={roles[key].person} size={38} />
                  <View className="flex-1">
                    <Text className="text-[12px] font-semibold text-ink">
                      {roles[key].label}
                    </Text>
                    <Text className="mt-1 text-[10px] text-muted">
                      {roles[key].person} · {roles[key].caption}
                    </Text>
                  </View>
                  {role === key && <Check size={16} color="#23664D" />}
                </Pressable>
              ))}
            </View>
          </Card>
          <Card className="p-5 lg:p-6">
            <SectionTitle title="Submission mode" />
            <View className="gap-3">
              {(["demo", "connected"] as Mode[]).map((value) => (
                <Pressable
                  key={value}
                  accessibilityRole="radio"
                  accessibilityLabel={value + " submission mode"}
                  accessibilityState={{ checked: mode === value }}
                  onPress={() => setMode(value)}
                  className={`flex-row items-start gap-3 rounded-xl border p-4 ${mode === value ? "border-forest bg-mint" : "border-line"}`}
                >
                  <Radio size={19} color="#638572" />
                  <View className="flex-1">
                    <Text className="text-[12px] font-semibold text-ink">
                      {value === "demo"
                        ? "Demo workspace"
                        : "Connected submissions"}
                    </Text>
                    <Text className="mt-1.5 text-[11px] leading-[18px] text-muted">
                      {value === "demo"
                        ? "Use sample projects and local requests. Photo selection, office review, and client decisions work without a server."
                        : "Upload new photos and descriptions to your running API. Reviews and decisions for those requests use the existing API routes."}
                    </Text>
                  </View>
                  {mode === value && <Check size={15} color="#23664D" />}
                </Pressable>
              ))}
            </View>
            <Text className="mt-4 text-[10px] leading-4 text-muted">
              Project names, titles, estimates, and schedule details are
              presentation data in both modes. They stay in this session; only
              the existing description, priority, and photo fields are uploaded.
            </Text>
          </Card>
        </View>
        <View className="w-full gap-5 xl:w-[310px]">
          <Card className="p-5">
            <View className="mb-4 flex-row items-center gap-2">
              <Wifi size={17} color="#23664D" />
              <Text className="text-[13px] font-semibold text-ink">
                Server connection
              </Text>
            </View>
            <Text className="mb-3 text-[10px] leading-4 text-muted">
              {API_URL ?? "Set EXPO_PUBLIC_API_URL in frontend/.env"}
            </Text>
            <Button variant="secondary" busy={checking} onPress={check}>
              Check backend
            </Button>
            <Text
              accessibilityLiveRegion="polite"
              className={`mt-3 text-[11px] leading-5 ${status === "Backend: ok" ? "text-forest" : "text-muted"}`}
            >
              {status}
            </Text>
          </Card>
          <Card className="p-5">
            <ShieldCheck size={23} color="#7B9A70" />
            <Text className="mb-2 mt-3 text-[13px] font-semibold text-ink">
              A safe space to demonstrate.
            </Text>
            <Text className="text-[11px] leading-5 text-muted">
              The default demo uses sample records. Activity updates remain
              inside the app; this demo does not deliver push notifications,
              email, or text messages.
            </Text>
          </Card>
          <Card className="p-5">
            <SectionTitle title="Start a fresh walkthrough" />
            <Text className="mb-4 text-[11px] leading-5 text-muted">
              Restore the sample workspace and clear this session’s requests.
              Connected uploads remain on your server.
            </Text>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onPress={() => setConfirm(true)}
            >
              Reset demo workspace
            </Button>
          </Card>
        </View>
      </View>
      <Modal
        visible={confirm}
        transparent
        animationType="fade"
        onRequestClose={() => setConfirm(false)}
      >
        <View className="flex-1 items-center justify-center bg-black/35 px-5">
          <Card className="w-full max-w-[400px] p-6">
            <View className="flex-row items-center justify-between">
              <Text className="text-[20px] font-bold text-ink">
                Start fresh?
              </Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Cancel reset"
                onPress={() => setConfirm(false)}
              >
                <X size={18} color="#74827C" />
              </Pressable>
            </View>
            <Text className="my-4 text-[12px] leading-5 text-muted">
              This resets local demo records and restores the sample projects.
              It does not delete files or records from the connected server.
            </Text>
            <Button
              onPress={() => {
                reset();
                setConfirm(false);
              }}
            >
              Restore sample workspace
            </Button>
          </Card>
        </View>
      </Modal>
    </AppShell>
  );
}
