import { Image } from "expo-image";
import { useLocalSearchParams } from "expo-router";
import {
  ArrowLeft,
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

import { requestJson } from "@/lib/api";
import type { Suggestion } from "@/features/change-orders/types";

import { useWorkspace } from "./context";
import {
  type WorkspaceChange,
  getProject,
  money,
  roles,
  shortDate,
  visibleHistory,
} from "./data";
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
  const { changes, role } = useWorkspace();
  const change = changes.find((item) => item.id === id);
  if (!change)
    return (
      <AppShell title="Request details">
        <Card>
          <EmptyState
            title="Request unavailable in this view"
            description="Return to your request list to choose a change available to this role."
            onAction={() => go("/requests")}
            action="View requests"
          />
        </Card>
      </AppShell>
    );
  return <ChangeDetail key={`${role}:${change.id}`} change={change} />;
}

function ChangeDetail({ change }: { change: WorkspaceChange }) {
  const { role, review, authorize, decide, refresh } = useWorkspace();
  const [amount, setAmount] = useState(String(change.amount));
  const [days, setDays] = useState(String(change.impactDays));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState<
    "approve" | "decline" | null
  >(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [originalScope, setOriginalScope] = useState("");
  const [suggestion, setSuggestion] = useState<Suggestion | null>(
    change.suggestion ?? null,
  );
  const [suggesting, setSuggesting] = useState(false);
  const [scope, setScope] = useState(change.approvedScope ?? change.description);
  const photoUris =
    change.photoUris ?? (change.photoUri ? [change.photoUri] : []);
  async function suggest() {
    setSuggesting(true);
    setError("");
    try {
      const result = await requestJson<Suggestion>(
        "/api/v1/changes/" + encodeURIComponent(change.id) + "/suggestion",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ original_scope: originalScope }),
        },
        60000,
      );
      setSuggestion(result);
      await refresh();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not generate a suggestion.",
      );
    } finally {
      setSuggesting(false);
    }
  }
  const project = getProject(change.projectId);
  const isApprover = role === "approver";
  const reviewable = ["submitted", "in_review", "authorized_to_proceed"].includes(change.status);
  const showTerms = role !== "subcontractor" && !reviewable;
  const history = visibleHistory(role, change);
  const stage =
    reviewable
      ? 0
      : change.status === "awaiting_gc"
        ? 1
        : 2;

  async function sendForReview() {
    if (busy) return;
    const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(amount.trim());
    const cost = match ? Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0")) : NaN;
    const impact = /^\d+$/.test(days.trim()) ? Number(days) : NaN;
    if (!Number.isSafeInteger(cost) || cost > 10_000_000_000 || !Number.isInteger(impact) || impact > 3650 || !scope.trim()) {
      setError("Enter a USD cost with at most two decimal places, 0–3650 whole days, and a work scope.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await review(change.id, cost, impact, scope);
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
    if (busy || !confirmation) return;
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
    <AppShell title={isApprover ? "Proposal details" : "Request details"}>
      <Pressable
        accessibilityRole="button"
        onPress={() => go("/requests")}
        className="mb-5 flex-row items-center gap-2 self-start py-1"
      >
        <ArrowLeft size={14} color="#74827C" />
        <Text className="text-[11px] text-muted">
          {isApprover ? "Back to approval queue" : "Back to requests"}
        </Text>
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
      {!isApprover && (
        <View className="mb-6 flex-row items-center rounded-2xl border border-line bg-white p-4">
          {[
            "Submitted",
            "Office review",
            change.severity === "high"
              ? "GC decision"
              : change.status === "declined"
                ? "Declined"
                : "Approver decision",
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
      )}

      <View
        className={`gap-5 lg:flex-row ${isApprover ? "flex-col-reverse" : "flex-col"}`}
      >
        <View className="min-w-0 flex-1 gap-5">
          <Card className="p-5 lg:p-6">
            <SectionTitle
              title={
                role === "subcontractor" ? "My site report" : "Requested work"
              }
            />
            <View className="mb-5 flex-row items-center justify-between">
              <View className="flex-row items-center gap-2.5">
                <Avatar name={change.author} size={34} />
                <View>
                  <Text className="text-[11px] font-semibold text-ink">
                    {change.author}
                  </Text>
                  <Text className="mt-1 text-[10px] text-muted">
                    {roles[change.submittedBy].label}
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
              <Text className="ml-auto text-[10px] text-muted">
                {photoUris.length
                  ? photoUris.length + " images"
                  : "Demo illustration"}
              </Text>
            </View>
            <View className="relative mt-4 overflow-hidden rounded-xl border border-line bg-canvas">
              {photoUris.length ? (
                photoUris.map((uri, index) => (
                  <View key={uri} className="relative">
                    <Image
                      source={{ uri }}
                      style={{ width: "100%", height: 260 }}
                      contentFit="contain"
                      accessibilityLabel={"Submitted site photo " + (index + 1)}
                    />
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={"Expand site photo " + (index + 1)}
                      onPress={() => setExpanded(uri)}
                      className="absolute bottom-3 right-3 rounded-lg bg-white p-3"
                    >
                      <Expand size={18} color="#23664D" />
                    </Pressable>
                  </View>
                ))
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
            <SectionTitle
              title={isApprover ? "Decision history" : "Request timeline"}
            />
            {history.map((event, i) => (
              <View key={event.id} className="flex-row gap-3">
                <View className="items-center">
                  <View
                    className={`h-7 w-7 items-center justify-center rounded-full ${i === history.length - 1 ? "bg-mint" : "bg-canvas"}`}
                  >
                    <Check size={12} color="#638572" />
                  </View>
                  {i < history.length - 1 && (
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
            <SectionTitle
              title={isApprover ? "Proposal terms" : "Project details"}
            />
            {showTerms && !!change.approvedScope && (
              <Text className="mb-4 text-[13px] leading-6 text-ink">
                {change.approvedScope}
              </Text>
            )}
            {showTerms && (
              <View className="mb-5 rounded-xl bg-canvas p-4">
                <Text className="text-[10px] text-muted">
                  {change.status === "approved"
                    ? "Approved change value"
                    : "Proposed change value"}
                </Text>
                <Text className="mt-2 text-[31px] font-semibold tracking-[-1px] text-ink">
                  {money(change.amount)}
                </Text>
                <View className="mt-3 flex-row items-center gap-1.5">
                  <CalendarDays size={12} color="#74827C" />
                  <Text className="text-[10px] text-muted">
                    {change.impactDays
                      ? `+${change.impactDays} ${change.impactDays === 1 ? "day" : "days"}`
                      : "No schedule extension"}
                  </Text>
                </View>
              </View>
            )}
            <Text className="mb-1 text-[10px] text-muted">Project</Text>
            <Text className="text-[12px] font-semibold text-ink">
              {project.name}
            </Text>
            <Text className="mt-1 text-[10px] leading-4 text-muted">
              {project.address}
            </Text>
            {role !== "subcontractor" && !isApprover && (
              <>
                <View className="my-4 h-px bg-line" />
                <Text className="mb-2 text-[10px] text-muted">
                  Project contact
                </Text>
                <View className="flex-row items-center gap-2">
                  <Avatar name={project.client} size={26} />
                  <Text className="text-[11px] text-ink">{project.client}</Text>
                </View>
              </>
            )}
          </Card>

          <Card className="border-[#CEDFCB] p-5">
            {role === "manager" && change.severity === "high" && ["submitted", "in_review"].includes(change.status) ? (
              <>
                <Text className="text-[15px] font-semibold text-ink">Authorize urgent work</Text>
                <Text className="my-4 text-[12px] leading-5 text-muted">Work may start before the estimate. This does not approve the cost; the estimator adds it and the GC decides afterward.</Text>
                <Button busy={busy} onPress={async () => {
                  if (busy) return;
                  setBusy(true); setError("");
                  try { await authorize(change.id); }
                  catch (cause) { setError(cause instanceof Error ? cause.message : "Could not authorize work."); }
                  finally { setBusy(false); }
                }}>Authorize work now</Button>
              </>
            ) : role === "office" && reviewable ? (
              <>
                <Text className="text-[15px] font-semibold text-ink">
                  Prepare the proposal
                </Text>
                <Text className="mb-4 mt-2 text-[11px] leading-[18px] text-muted">
                  Add a proposed cost and schedule impact before moving this
                  change forward.
                </Text>
                {change.source === "connected" && (
                  <View className="mb-5 gap-3">
                    <Text className="text-[12px] font-semibold text-ink">
                      AI estimate assistant
                    </Text>
                    <Text className="text-[11px] leading-5 text-muted">
                      Paste the approved original scope. AI compares it with
                      this report. Photos are context for people. Review all assumptions
                      before using the suggestion.
                    </Text>
                    <TextInput
                      accessibilityLabel="Original approved scope"
                      value={originalScope}
                      onChangeText={setOriginalScope}
                      multiline
                      maxLength={10000}
                      placeholder="Original approved scope of work"
                      className="min-h-[90px] rounded-xl border border-line p-3 text-ink"
                    />
                    <Button
                      variant="secondary"
                      onPress={suggest}
                      busy={suggesting}
                      disabled={busy || originalScope.trim().length < 10}
                    >
                      Generate suggestion
                    </Button>
                    {!!suggestion && (
                      <View className="gap-2 rounded-xl bg-canvas p-3">
                        <Text className="text-[12px] font-semibold text-ink">
                          Unverified suggestion ·{" "}
                          {suggestion.in_scope
                            ? "Likely in scope"
                            : "Likely extra work"}
                        </Text>
                        <Text className="text-[12px] text-ink">
                          {suggestion.scope}
                        </Text>
                        <Text className="text-[12px] text-ink">
                          {money(suggestion.amount)} · {suggestion.impact_days}{" "}
                          additional days
                        </Text>
                        <Text className="text-[11px] leading-5 text-muted">
                          {suggestion.rationale}
                        </Text>
                        <Button
                          variant="secondary"
                          disabled={busy}
                          onPress={() => {
                            setAmount(String(suggestion.amount));
                            setDays(String(suggestion.impact_days));
                            setScope(suggestion.scope);
                          }}
                        >
                          Use suggestion for review
                        </Button>
                      </View>
                    )}
                  </View>
                )}
                <Text className="mb-2 text-[10px] font-semibold text-ink">
                  Proposed work scope
                </Text>
                <TextInput
                  accessibilityLabel="Proposed work scope"
                  value={scope}
                  onChangeText={setScope}
                  multiline
                  maxLength={2000}
                  className="mb-4 min-h-[90px] rounded-xl border border-line bg-canvas p-3 text-[13px] text-ink"
                />
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
                    The manager authorizes urgent work before estimation. The GC still approves or declines the cost.
                  </Text>
                )}
                <Button onPress={sendForReview} busy={busy} icon={Send}>
                  Send estimate to GC
                </Button>
              </>
            ) : isApprover && change.source === "demo" && change.status === "awaiting_gc" ? (
              <>
                <View className="mb-3 h-10 w-10 items-center justify-center rounded-xl bg-mint">
                  <CheckCircle2 size={20} color="#23664D" />
                </View>
                <Text className="text-[16px] font-semibold text-ink">
                  Record your decision
                </Text>
                <Text className="mb-5 mt-2 text-[11px] leading-[18px] text-muted">
                  Review the requested work, proposed cost, and schedule impact.
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
            ) : change.status === "approved" || change.status === "declined" ? (
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
                    ? "The project work order now includes this scope, cost, schedule impact, and photos."
                    : "This change was declined and remains in the project record."}
                </Text>
              </>
            ) : (
              <>
                <Text className="text-[15px] font-semibold text-ink">
                  {change.status === "authorized_to_proceed"
                    ? "Work authorized · estimate pending"
                    : change.status === "submitted"
                    ? "Waiting for estimator review"
                    : "Waiting for a decision"}
                </Text>
                <Text className="mb-4 mt-2 text-[11px] leading-[18px] text-muted">
                  {change.status === "submitted"
                    ? "The estimator will review the site report and prepare the terms."
                    : "The GC still decides the cost after the estimator submits the terms."}
                </Text>
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
              {change.title} · {money(change.amount)}. Your decision will be
              added to the request timeline.
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
        visible={expanded !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setExpanded(null)}
      >
        <View className="flex-1 items-center justify-center bg-black/90">
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close photo"
            onPress={() => setExpanded(null)}
            className="absolute right-6 top-12 z-10 rounded-full bg-white/20 p-3"
          >
            <X size={20} color="white" />
          </Pressable>
          <Image
            source={{ uri: expanded ?? undefined }}
            style={{ width: "100%", height: "80%" }}
            contentFit="contain"
          />
        </View>
      </Modal>
    </AppShell>
  );
}
