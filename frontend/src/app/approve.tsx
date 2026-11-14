import { Image } from "expo-image";
import { useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { ScrollView, Text, View } from "react-native";

import type { ChangeOrder } from "@/features/change-orders/types";
import { Button, Card } from "@/features/workspace/ui";
import { API_URL, requestJson } from "@/lib/api";

type ApprovalStatus = "submitted" | "in_review" | "authorized_to_proceed" | "awaiting_gc" | "awaiting_client" | "approved" | "declined" | "rejected" | "withdrawn";
type Proposal = Omit<ChangeOrder, "status"> & {
  status: ApprovalStatus;
  proposed_cost_cents?: number | null;
  requested_timeline_days?: number | null;
  currency?: string;
};
const labels: Record<ApprovalStatus, string> = {
  submitted: "Not ready for a decision", in_review: "Estimate in progress",
  authorized_to_proceed: "Work authorized · estimate pending",
  awaiting_gc: "Awaiting your decision", awaiting_client: "Awaiting your decision",
  approved: "Approved", declined: "Declined", rejected: "Declined", withdrawn: "Withdrawn",
};

export default function ApprovalLinkScreen() {
  const { token } = useLocalSearchParams<{ token?: string | string[] }>();
  const validToken = typeof token === "string" ? token : "";
  // A new link starts a fresh view, including confirmation and request state.
  return <ProposalReview key={validToken} token={validToken} />;
}

function ProposalReview({ token }: { token: string }) {
  const [change, setChange] = useState<Proposal | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const saving = useRef(false);
  const [attempt, setAttempt] = useState(0);
  const [confirmation, setConfirmation] = useState<"approve" | "decline" | null>(null);
  useEffect(() => {
    let active = true;
    if (token) {
      requestJson<Proposal>("/api/v1/approval-session?token=" + encodeURIComponent(token))
        .then(result => { if (active) setChange(result); })
        .catch(cause => {
          if (active) setError(cause instanceof Error ? cause.message : "Could not open proposal.");
        });
    }
    return () => { active = false; };
  }, [token, attempt]);

  async function decide() {
    if (!confirmation || saving.current || !change) return;
    saving.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await requestJson<{ status: ApprovalStatus }>(
        "/api/v1/approval-session/" + confirmation + "?token=" + encodeURIComponent(token),
        { method: "POST" },
      );
      // The POST response is authoritative. A consumed link need not support
      // another GET, and a read failure must not invite a duplicate decision.
      setChange({ ...change, status: result.status });
      setConfirmation(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save decision.");
      // Re-open the proposal before retrying an uncertain network result.
      setChange(null);
      setConfirmation(null);
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }

  const awaiting = change && ["awaiting_gc", "awaiting_client"].includes(change.status);
  const cost = change?.proposed_cost_cents != null ? change.proposed_cost_cents / 100 : change?.amount;
  const currency = change?.currency ?? "USD";
  const formattedCost = cost == null ? "Not estimated yet" : new Intl.NumberFormat("en-US", {
    style: "currency", currency: /^[A-Z]{3}$/.test(currency) ? currency : "USD",
  }).format(cost);

  return (
    <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, alignItems: "center" }}>
      <View className="w-full max-w-[640px] gap-4">
        <Text accessibilityRole="header" className="text-[12px] font-semibold text-forest">CHANGEORDER · GC PROPOSAL REVIEW</Text>
        <Text className="text-[13px] leading-6 text-muted">No account needed. Opening this link does not approve or decline anything.</Text>
        {!token && <Text accessibilityRole="alert">This link is incomplete. Ask the sender for the complete approval link.</Text>}
        {!!error && <Card className="gap-3 p-4">
          <Text accessibilityRole="alert" className="text-red-700">{error}</Text>
          <Text className="text-[12px] leading-5 text-muted">If the link has expired, was replaced, or is invalid, ask the sender for a new one. If your connection dropped, check the current proposal before deciding again.</Text>
          <Button variant="secondary" onPress={() => { setError(""); setAttempt(value => value + 1); }}>Reload proposal</Button>
        </Card>}
        {!change && !!token && !error && <Text accessibilityLiveRegion="polite">Loading proposal…</Text>}
        {!!change && <Card className="gap-4 p-5">
          <Text accessibilityRole="header" className="text-[24px] font-bold text-ink">{change.title}</Text>
          <Text accessibilityLiveRegion="polite" className="text-[12px] font-semibold text-forest">{labels[change.status]}</Text>
          <Text className="text-[14px] leading-6 text-ink">{change.approved_scope ?? change.description}</Text>
          <Text className="text-[22px] font-semibold text-ink">{formattedCost}</Text>
          <Text className="text-muted">{change.requested_timeline_days ?? change.impact_days} additional calendar days</Text>
          {change.photo_keys.map((key, index) => <Image key={key} source={{ uri: API_URL + "/uploads/" + encodeURIComponent(key) }} style={{ width: "100%", height: 240 }} contentFit="contain" accessibilityLabel={"Site photo " + (index + 1)} />)}
          {awaiting && (confirmation ? <>
            <Text className="text-[15px] font-semibold text-ink">{confirmation === "approve" ? "Approve these exact terms?" : "Decline this proposal?"}</Text>
            <Text className="text-[13px] text-muted">{formattedCost} · {change.requested_timeline_days ?? change.impact_days} additional calendar days. This decision is final for this proposal.</Text>
            <Button busy={busy} onPress={decide}>{confirmation === "approve" ? "Confirm approval" : "Confirm decline"}</Button>
            <Button variant="quiet" disabled={busy} onPress={() => setConfirmation(null)}>Keep reviewing</Button>
          </> : <>
            <Button onPress={() => setConfirmation("approve")}>Approve change</Button>
            <Button variant="danger" onPress={() => setConfirmation("decline")}>Decline change</Button>
          </>)}
          {change.status === "approved" && <Text className="text-forest">Your approval was recorded. You can close this page.</Text>}
          {["declined", "rejected"].includes(change.status) && <Text className="text-ink">Your decline was recorded. You can close this page.</Text>}
        </Card>}
      </View>
    </ScrollView>
  );
}
