import { ChangeOrderForm } from "@/features/change-orders/change-order-form";
import { AppShell } from "@/features/workspace/shell";

export default function NewChangeScreen() {
  return (
    <AppShell title="New change request">
      <ChangeOrderForm />
    </AppShell>
  );
}
