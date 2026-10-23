import { Image } from "expo-image";
import { useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  Expand,
  FileText,
  Send,
  X,
} from "lucide-react-native";
import { useState } from "react";
import { Modal, Pressable, Text, TextInput, View } from "react-native";

import { useWorkspace } from "./context";
import { getProject, money, shortDate } from "./data";
import { AppShell, go } from "./shell";
import {
  Avatar,
  Button,
  Card,
  EmptyState,
  PriorityBadge,
  ProjectArt,
  SectionTitle,
  StatusBadge,
} from "./ui";

export function ChangeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { changes, role, setRole, review, decide } = useWorkspace();
  const change = changes.find((item) => item.id === id);
  const [amount, setAmount] = useState(String(change?.amount ?? 0));
  const [days, setDays] = useState(String(change?.impactDays ?? 0));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState<
    "approve" | "decline" | null
  >(null);
  const [expanded, setExpanded] = useState(false);
  if (!change)
    return (
      <AppShell title="Request details">
        <Card>
          <EmptyState
            title="Request not found"
            description="This workspace may have been reset. Return to requests to choose another change."
            onAction={() => go("/requests")}
            action="View requests"
          />
        </Card>
      </AppShell>
    );
  const project = getProject(change.projectId);
  const stage =
    change.status === "submitted"
      ? 0
      : change.status === "awaiting_client"
        ? 1
        : 2;

  async function sendForReview() {
    if (busy || !change) return;
    const cost = Number(amount),
      impact = Number(days);
    if (
      !Number.isFinite(cost) ||
      cost < 0 ||
      !Number.isInteger(impact) ||
      impact < 0
    ) {
      setError("Enter a valid non-negative amount and whole number of days.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await review(change.id, cost, impact);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Review could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function decideChange() {
    if (busy || !change || !confirmation) return;
    setBusy(true);
    setError("");
    try {
      await decide(change.id, confirmation === "approve");
      setConfirmation(null);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "The decision could not be saved.",
      );
      setConfirmation(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Request details">
      <Pressable
        accessibilityRole="button"
        onPress={() => go("/requests")}
        className="mb-5 flex-row items-center gap-2 self-start py-1"
      >
        <ArrowLeft size={14} color="#74827C" />
        <Text className="text-[11px] text-muted">Back to change requests</Text>
      </Pressable>
      <View className="mb-6 flex-row flex-wrap items-start justify-between gap-4">
        <View className="flex-1 gap-2">
          <View className="flex-row items-center gap-2">
            <Text className="text-[10px] font-semibold tracking-wider text-muted">
              {change.code}
            </Text>
            <Text className="rounded bg-white px-2 py-0.5 text-[9px] text-muted">
              {change.source === "demo" ? "DEMO" : "CONNECTED"}
            </Text>
          </View>
          <Text
            accessibilityRole="header"
            className="text-[27px] font-bold leading-9 tracking-[-0.6px] text-ink"
          >
            {change.title}
          </Text>
          <Text className="text-[12px] text-muted">
            {project.name} · Submitted {shortDate(change.createdAt)}
          </Text>
        </View>
        <StatusBadge status={change.status} />
      </View>
      <View className="mb-6 flex-row items-center rounded-2xl border border-line bg-white p-4">
        {[
          "Submitted",
          "Office review",
          change.severity === "high"
            ? "Office approval"
            : change.status === "rejected"
              ? "Declined"
              : "Client decision",
        ].map((label, i) => (
          <View key={label} className="flex-1 flex-row items-center gap-2">
            <View
              className={`h-6 w-6 items-center justify-center rounded-full ${i <= stage ? "bg-forest" : "bg-canvas"}`}
            >
              {i < stage ? (
                <Check size={12} color="white" />
              ) : (
                <Text
                  className={`text-[10px] font-semibold ${i <= stage ? "text-white" : "text-muted"}`}
                >
                  {i + 1}
                </Text>
              )}
            </View>
            <Text
              className={`flex-1 text-[10px] ${i <= stage ? "font-semibold text-ink" : "text-muted"}`}
            >
              {label}
            </Text>
            {i < 2 && <ChevronRight size={12} color="#C3CDC2" />}
          </View>
        ))}
      </View>

      <View className="flex-col gap-5 lg:flex-row">
        <View className="min-w-0 flex-1 gap-5">
          <Card className="p-5 lg:p-6">
            <SectionTitle title="The requested change" />
            <View className="mb-5 flex-row items-center justify-between">
              <View className="flex-row items-center gap-2.5">
                <Avatar name={change.author} size={34} />
                <View>
                  <Text className="text-[11px] font-semibold text-ink">
                    {change.author}
                  </Text>
                  <Text className="mt-1 text-[10px] text-muted">
                    Field contractor
                  </Text>
                </View>
              </View>
              <PriorityBadge high={change.severity === "high"} />
            </View>
            <Text className="text-[13px] leading-[23px] text-[#5F7166]">
              {change.description}
            </Text>
            <View className="my-5 h-px bg-line" />
            <View className="flex-row items-center gap-2">
              <FileText size={15} color="#74827C" />
              <Text className="text-[11px] font-semibold text-ink">
                Site attachment
              </Text>
              <Text className="ml-auto text-[10px] text-muted">1 image</Text>
            </View>
            <View className="relative mt-4 overflow-hidden rounded-xl border border-line bg-canvas">
              {change.photoUri ? (
                <>
                  <Image
                    source={{ uri: change.photoUri }}
                    style={{ width: "100%", height: 300 }}
                    contentFit="contain"
                    accessibilityLabel="Submitted site photo"
                  />
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Expand site photo"
                    onPress={() => setExpanded(true)}
                    className="absolute bottom-3 right-3 rounded-lg bg-white p-2"
                  >
                    <Expand size={15} color="#23664D" />
                  </Pressable>
                </>
              ) : (
                <>
                  <ProjectArt
                    height={240}
                    variant={
                      project.id === "harbor"
                        ? 1
                        : project.id === "cedar"
                          ? 2
                          : 0
                    }
                  />
                  <View className="absolute bottom-3 left-3 rounded-md bg-white/90 px-2 py-1">
                    <Text className="text-[9px] text-muted">
                      Sample site illustration
                    </Text>
                  </View>
                </>
              )}
            </View>
          </Card>

          <Card className="p-5 lg:p-6">
            <SectionTitle title="Request timeline" />
            {change.history.map((event, i) => (
              <View key={event.id} className="flex-row gap-3">
                <View className="items-center">
                  <View
                    className={`h-7 w-7 items-center justify-center rounded-full ${i === change.history.length - 1 ? "bg-mint" : "bg-canvas"}`}
                  >
                    <Check size={12} color="#638572" />
                  </View>
                  {i < change.history.length - 1 && (
                    <View className="my-1 w-px flex-1 bg-line" />
                  )}
                </View>
                <View className="min-h-[65px] flex-1 pb-5">
                  <Text className="text-[12px] font-semibold text-ink">
                    {event.title}
                  </Text>
                  <Text className="mt-1.5 text-[10px] text-muted">
                    {event.person} · {shortDate(event.time)}
                  </Text>
                </View>
              </View>
            ))}
          </Card>
        </View>

        <View className="w-full gap-5 lg:w-[310px]">
          <Card className="p-5">
            <SectionTitle title="Change summary" />
            <View className="mb-5 rounded-xl bg-canvas p-4">
              <Text className="text-[10px] text-muted">
                {change.status === "approved"
                  ? "Approved change value"
                  : "Proposed change value"}
              </Text>
              <Text className="mt-2 text-[31px] font-semibold tracking-[-1px] text-ink">
                {change.amount ? money(change.amount) : "To estimate"}
              </Text>
              <View className="mt-3 flex-row items-center gap-1.5">
                <CalendarDays size={12} color="#74827C" />
                <Text className="text-[10px] text-muted">
                  {change.impactDays
                    ? "+" + change.impactDays + " day schedule impact"
                    : "No schedule extension"}
                </Text>
              </View>
            </View>
            <Text className="mb-1 text-[10px] text-muted">Project</Text>
            <Text className="text-[12px] font-semibold text-ink">
              {project.name}
            </Text>
            <Text className="mt-1 text-[10px] leading-4 text-muted">
              {project.address}
            </Text>
            <View className="my-4 h-px bg-line" />
            <Text className="mb-2 text-[10px] text-muted">Client / owner</Text>
            <View className="flex-row items-center gap-2">
              <Avatar name={project.client} size={26} />
              <Text className="text-[11px] text-ink">{project.client}</Text>
            </View>
          </Card>

          <Card className="border-[#CEDFCB] p-5">
            {role === "office" && change.status === "submitted" ? (
              <>
                <Text className="text-[15px] font-semibold text-ink">
                  Ready for your review
                </Text>
                <Text className="mb-4 mt-2 text-[11px] leading-[18px] text-muted">
                  Add a proposed cost and schedule impact before moving this
                  change forward.
                </Text>
                <Text className="mb-2 text-[10px] font-semibold text-ink">
                  Proposed cost ($)
                </Text>
                <TextInput
                  accessibilityLabel="Proposed cost"
                  value={amount}
                  onChangeText={setAmount}
                  keyboardType="decimal-pad"
                  className="mb-4 min-h-[44px] rounded-xl border border-line bg-canvas px-3 text-[13px] text-ink"
                />
                <Text className="mb-2 text-[10px] font-semibold text-ink">
                  Additional days
                </Text>
                <TextInput
                  accessibilityLabel="Additional days"
                  value={days}
                  onChangeText={setDays}
                  keyboardType="number-pad"
                  className="mb-4 min-h-[44px] rounded-xl border border-line bg-canvas px-3 text-[13px] text-ink"
                />
                {change.severity === "high" && (
                  <Text className="mb-4 text-[10px] leading-4 text-ochre">
                    High-priority changes can be approved directly by the
                    office.
                  </Text>
                )}
                <Button onPress={sendForReview} busy={busy} icon={Send}>
                  {change.severity === "high"
                    ? "Approve urgent change"
                    : "Send for client approval"}
                </Button>
              </>
            ) : role === "client" && change.status === "awaiting_client" ? (
              <>
                <View className="mb-3 h-10 w-10 items-center justify-center rounded-xl bg-mint">
                  <CheckCircle2 size={20} color="#23664D" />
                </View>
                <Text className="text-[16px] font-semibold text-ink">
                  Your decision keeps it moving.
                </Text>
                <Text className="mb-5 mt-2 text-[11px] leading-[18px] text-muted">
                  Review the description, photo, and proposed cost. Approve when
                  you’re ready, or decline the change.
                </Text>
                <View className="gap-2">
                  <Button
                    icon={Check}
                    onPress={() => setConfirmation("approve")}
                  >
                    Approve change
                  </Button>
                  <Button
                    variant="danger"
                    onPress={() => setConfirmation("decline")}
                  >
                    Decline change
                  </Button>
                </View>
              </>
            ) : change.status === "approved" || change.status === "rejected" ? (
              <>
                <CheckCircle2
                  size={25}
                  color={change.status === "approved" ? "#23664D" : "#B54742"}
                />
                <Text className="mt-3 text-[16px] font-semibold text-ink">
                  {change.status === "approved"
                    ? "Approved and recorded."
                    : "Decision recorded."}
                </Text>
                <Text className="mt-2 text-[11px] leading-[18px] text-muted">
                  {change.status === "approved"
                    ? "The field team can move forward with the approved change."
                    : "This change was declined and remains in the project record."}
                </Text>
              </>
            ) : (
              <>
                <Text className="text-[15px] font-semibold text-ink">
                  {change.status === "submitted"
                    ? "Next up: office review"
                    : "Waiting on client approval"}
                </Text>
                <Text className="mb-4 mt-2 text-[11px] leading-[18px] text-muted">
                  {change.status === "submitted"
                    ? "The office will review the request and prepare it for a decision."
                    : "The office has reviewed this change. It’s ready for the client."}
                </Text>
                <Button
                  variant="secondary"
                  icon={ArrowRight}
                  onPress={() =>
                    setRole(change.status === "submitted" ? "office" : "client")
                  }
                >
                  {change.status === "submitted"
                    ? "Preview office view"
                    : "Preview client view"}
                </Button>
              </>
            )}
            {!!error && (
              <Text
                accessibilityRole="alert"
                className="mt-4 rounded-lg bg-red-50 p-3 text-[11px] leading-5 text-red-700"
              >
                {error}
              </Text>
            )}
          </Card>
        </View>
      </View>

      <Modal
        visible={confirmation !== null}
        transparent
        animationType="fade"
        onRequestClose={() => {
          if (!busy) setConfirmation(null);
        }}
      >
        <View className="flex-1 items-center justify-center bg-black/35 px-5">
          <Card className="w-full max-w-[420px] p-6">
            <Text className="text-[22px] font-bold text-ink">
              {confirmation === "approve"
                ? "Approve this change?"
                : "Decline this change?"}
            </Text>
            <Text className="mb-5 mt-3 text-[13px] leading-6 text-muted">
              {change.title}
              {change.amount ? " · " + money(change.amount) : ""}. Your decision
              will be added to the request timeline.
            </Text>
            <View className="gap-2">
              <Button
                busy={busy}
                variant={confirmation === "decline" ? "danger" : "primary"}
                onPress={decideChange}
              >
                {confirmation === "approve"
                  ? "Confirm approval"
                  : "Confirm decline"}
              </Button>
              <Button
                variant="quiet"
                disabled={busy}
                onPress={() => setConfirmation(null)}
              >
                Keep reviewing
              </Button>
            </View>
          </Card>
        </View>
      </Modal>
      <Modal
        visible={expanded}
        transparent
        animationType="fade"
        onRequestClose={() => setExpanded(false)}
      >
        <View className="flex-1 items-center justify-center bg-black/90">
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close photo"
            onPress={() => setExpanded(false)}
            className="absolute right-6 top-12 z-10 rounded-full bg-white/20 p-3"
          >
            <X size={20} color="white" />
          </Pressable>
          <Image
            source={{ uri: change.photoUri }}
            style={{ width: "100%", height: "80%" }}
            contentFit="contain"
          />
        </View>
      </Modal>
    </AppShell>
  );
}
