import { Image } from "expo-image";
import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import type { ChangeOrder } from "@/features/change-orders/types";
import { money, statusLabels } from "@/features/workspace/data";
import { Button, Card } from "@/features/workspace/ui";
import { API_URL, requestJson } from "@/lib/api";

export default function ApprovalLinkScreen() {
  const { token } = useLocalSearchParams<{ token: string }>();
  const [change, setChange] = useState<ChangeOrder | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState<
    "approve" | "decline" | null
  >(null);
  useEffect(() => {
    let active = true;
    if (token)
      requestJson<ChangeOrder>(
        "/api/v1/approval-session?token=" + encodeURIComponent(token),
      )
        .then((result) => {
          if (active) setChange(result);
        })
        .catch((cause) => {
          if (active)
            setError(
              cause instanceof Error
                ? cause.message
                : "Could not open proposal.",
            );
        });
    return () => {
      active = false;
    };
  }, [token]);
  async function decide() {
    if (!confirmation || busy) return;
    setBusy(true);
    setError("");
    try {
      await requestJson(
        "/api/v1/approval-session/" +
          confirmation +
          "?token=" +
          encodeURIComponent(token),
        { method: "POST" },
      );
      setChange(
        await requestJson<ChangeOrder>(
          "/api/v1/approval-session?token=" + encodeURIComponent(token),
        ),
      );
      setConfirmation(null);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not save decision.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <ScrollView
      contentContainerStyle={{
        padding: 20,
        paddingTop: 60,
        alignItems: "center",
      }}
    >
      <View className="w-full max-w-[640px] gap-4">
        <Text className="text-[12px] font-semibold text-forest">
          CHANGEORDER · PROPOSAL REVIEW
        </Text>
        {!token && (
          <Text>Open the complete approval link supplied by your office.</Text>
        )}
        {!!error && (
          <Text accessibilityRole="alert" className="text-red-700">
            {error}
          </Text>
        )}
        {!change && !!token && !error && <Text>Loading proposal…</Text>}
        {!!change && (
          <Card className="gap-4 p-5">
            <Text className="text-[24px] font-bold text-ink">
              {change.title}
            </Text>
            <Text className="text-[12px] font-semibold text-forest">
              {statusLabels[change.status]}
            </Text>
            <Text className="text-[14px] leading-6 text-ink">
              {change.approved_scope ?? change.description}
            </Text>
            <Text className="text-[22px] font-semibold text-ink">
              {money(change.amount)}
            </Text>
            <Text className="text-muted">
              {change.impact_days} additional days
            </Text>
            {change.photo_keys.map((key, index) => (
              <Image
                key={key}
                source={{
                  uri: API_URL + "/uploads/" + encodeURIComponent(key),
                }}
                style={{ width: "100%", height: 240 }}
                contentFit="contain"
                accessibilityLabel={"Site photo " + (index + 1)}
              />
            ))}
            {["awaiting_gc", "awaiting_client"].includes(change.status) &&
              (confirmation ? (
                <>
                  <Text className="text-[15px] font-semibold text-ink">
                    {confirmation === "approve"
                      ? "Approve these terms and update the work order?"
                      : "Decline this proposal?"}
                  </Text>
                  <Button busy={busy} onPress={decide}>
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
                </>
              ) : (
                <>
                  <Button onPress={() => setConfirmation("approve")}>
                    Approve change
                  </Button>
                  <Button
                    variant="danger"
                    onPress={() => setConfirmation("decline")}
                  >
                    Decline change
                  </Button>
                </>
              ))}
            {change.status === "approved" && (
              <Text className="text-forest">
                Approved. The project work order has been updated automatically.
              </Text>
            )}
          </Card>
        )}
      </View>
    </ScrollView>
  );
}
