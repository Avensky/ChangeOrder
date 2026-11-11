import { AppShell, go } from "@/features/workspace/shell";
import { Card, EmptyState } from "@/features/workspace/ui";

export default function NotFound() {
  return (
    <AppShell title="Page not found">
      <Card>
        <EmptyState
          title="This page took a wrong turn."
          description="Head back to your workspace to keep the project moving."
          action="Back to overview"
          onAction={() => go("/")}
        />
      </Card>
    </AppShell>
  );
}
