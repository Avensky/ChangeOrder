import { ChangeOrderForm } from "@/features/change-orders/change-order-form";
import { useWorkspace } from "@/features/workspace/context";
import { isSubmitterRole } from "@/features/workspace/data";
import { AppShell, go } from "@/features/workspace/shell";
import { Card, EmptyState } from "@/features/workspace/ui";

export default function NewChangeScreen() {
  const { role } = useWorkspace();
  return (
    <AppShell title="New change request">
      {isSubmitterRole(role) ? (
        <ChangeOrderForm key={role} />
      ) : (
        <Card>
          <EmptyState
            title="Submissions are handled on site"
            description="Switch to Contractor or Subcontractor to report a site change."
            action={
              role === "approver" ? "Open approval queue" : "Open review queue"
            }
            onAction={() => go("/requests")}
          />
        </Card>
      )}
    </AppShell>
  );
}
