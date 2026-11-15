import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { useWorkspace } from "@/features/workspace/context";
import { getProject, money } from "@/features/workspace/data";
import { AppShell, openChange } from "@/features/workspace/shell";
import { Button, Card, PageHeading } from "@/features/workspace/ui";
import { requestJson } from "@/lib/api";

type WorkOrder = {
  revision: number;
  additional_amount: number;
  additional_days: number;
  changes: {
    change_id: string;
    title: string;
    scope: string;
    amount: number;
    impact_days: number;
    photo_keys: string[];
  }[];
};
export default function WorkOrderScreen() {
  const { project: id } = useLocalSearchParams<{ project: string }>();
  const { mode, role, changes } = useWorkspace();
  const project = getProject(id);
  const [order, setOrder] = useState<WorkOrder | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (mode !== "connected" || role === "subcontractor") return;
    let active = true;
    async function load() {
      try {
        const result = await requestJson<WorkOrder>(
          "/api/v1/projects/" + encodeURIComponent(project.id) + "/work-order",
        );
        if (active) {
          setOrder(result);
          setError("");
        }
      } catch (cause) {
        if (active)
          setError(
            cause instanceof Error
              ? cause.message
              : "Could not load work order.",
          );
      }
    }
    void load();
    const timer = setInterval(() => {
      void load();
    }, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [mode, project.id, role]);
  const approved = changes.filter(
    (c) => c.projectId === project.id && c.status === "approved",
  );
  const display =
    mode === "connected"
      ? order
      : {
          revision: approved.length,
          additional_amount: approved.reduce((sum, c) => sum + c.amount, 0),
          additional_days: approved.reduce((sum, c) => sum + c.impactDays, 0),
          changes: approved.map((c) => ({
            change_id: c.id,
            title: c.title,
            scope: c.approvedScope ?? c.description,
            amount: c.amount,
            impact_days: c.impactDays,
            photo_keys: c.photoUris ?? [],
          })),
        };
  return (
    <AppShell title="Project work order">
      <PageHeading
        title={project.name + " work order"}
        description="Approved changes are added automatically. Pending and declined changes do not affect these totals."
      />
      {role === "subcontractor" ? (
        <Card className="p-5">
          <Text>View your submitted changes from the request list.</Text>
        </Card>
      ) : (
        <>
          {!!error && (
            <Text accessibilityRole="alert" className="mb-4 text-red-700">
              {error}
            </Text>
          )}
          {!display ? (
            <Text>Loading work order…</Text>
          ) : (
            <View className="gap-4">
              <Card className="gap-3 p-5">
                <Text className="text-[12px] font-semibold text-forest">
                  Revision {display.revision} ·{" "}
                  {mode === "demo" ? "Demo" : "Saved on server"}
                </Text>
                <Text className="text-[24px] font-bold text-ink">
                  {money(project.budget + display.additional_amount)}
                </Text>
                <Text className="text-[12px] text-muted">
                  Sample base budget {money(project.budget)} + approved changes{" "}
                  {money(display.additional_amount)}
                </Text>
                <Text className="text-[12px] text-muted">
                  {display.additional_days} additional days · schedule impacts
                  are added sequentially
                </Text>
              </Card>
              {display.changes.length === 0 && (
                <Text className="text-muted">No approved changes yet.</Text>
              )}
              {display.changes.map((c) => (
                <Card key={c.change_id} className="gap-3 p-5">
                  <Text className="text-[17px] font-semibold text-ink">
                    {c.title}
                  </Text>
                  <Text className="text-[13px] leading-6 text-ink">
                    {c.scope}
                  </Text>
                  <Text className="text-[12px] text-muted">
                    {money(c.amount)} · +{c.impact_days} days ·{" "}
                    {c.photo_keys.length} photos
                  </Text>
                  <Button
                    variant="secondary"
                    onPress={() => openChange(c.change_id)}
                  >
                    View approved change and photos
                  </Button>
                </Card>
              ))}
            </View>
          )}
        </>
      )}
    </AppShell>
  );
}
