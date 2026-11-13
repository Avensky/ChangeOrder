import {
  ArrowRight,
  ArrowUpRight,
  Camera,
  ClipboardCheck,
  Plus,
} from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { useWorkspace } from "./context";
import { getProject, money, projects, type WorkspaceChange } from "./data";
import { AppShell, go, openChange } from "./shell";
import {
  Button,
  Card,
  EmptyState,
  PageHeading,
  PriorityBadge,
  RequestRow,
  SectionTitle,
} from "./ui";

type DashboardProps = { changes: WorkspaceChange[] };

function ContractorDashboard({ changes }: DashboardProps) {
  const openChanges = changes.filter(
    (change) =>
      change.status === "submitted" || change.status === "awaiting_client",
  );
  return (
    <>
      <PageHeading
        title="Project coordination"
        description="See which jobs have open changes and where the team is waiting for a decision."
        action={
          <Button icon={Plus} onPress={() => go("/new")}>
            New change request
          </Button>
        }
      />
      <View className="mb-6">
        <SectionTitle
          title="Active projects"
          action="View projects"
          onAction={() => go("/projects")}
        />
        <View className="flex-row flex-wrap gap-3">
          {projects.map((project) => {
            const open = openChanges.filter(
              (change) => change.projectId === project.id,
            );
            const awaiting = open.filter(
              (change) => change.status === "awaiting_client",
            );
            return (
              <Pressable
                key={project.id}
                accessibilityRole="button"
                accessibilityLabel={`View change requests for ${project.name}`}
                onPress={() => go("/requests?project=" + project.id)}
                className="min-w-[160px] flex-1 gap-3 rounded-card border border-line bg-white p-4 hover:border-[#B8CDBE] active:bg-canvas"
              >
                <View className="flex-row items-center justify-between">
                  <View
                    className="h-9 w-9 items-center justify-center rounded-xl"
                    style={{ backgroundColor: project.color }}
                  >
                    <Text className="text-[10px] font-bold text-forest">
                      {project.initials}
                    </Text>
                  </View>
                  <ArrowUpRight size={16} color="#74827C" />
                </View>
                <Text className="text-[14px] font-semibold text-ink">
                  {project.name}
                </Text>
                <View className="flex-row flex-wrap gap-x-3 gap-y-1">
                  <Text className="text-[11px] text-muted">
                    {open.length} open
                  </Text>
                  <Text className="text-[11px] text-muted">
                    {awaiting.length} awaiting decision
                  </Text>
                </View>
                <View className="h-1 overflow-hidden rounded-full bg-canvas">
                  <View
                    className="h-full rounded-full bg-forest"
                    style={{ width: `${project.progress}%` }}
                  />
                </View>
                <Text className="text-[10px] text-muted">
                  {project.progress}% complete
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>
      <RequestSection
        title="Open changes across jobs"
        changes={openChanges}
        action="View all project requests"
        onAction={() => go("/requests")}
        emptyTitle="No open changes"
        emptyDescription="Submitted changes and pending decisions will appear here."
      />
    </>
  );
}

function SubcontractorDashboard({ changes }: DashboardProps) {
  const inReview = changes.filter(
    (change) => change.status === "submitted",
  ).length;
  const awaiting = changes.filter(
    (change) => change.status === "awaiting_client",
  ).length;
  return (
    <>
      <PageHeading title="Field submissions" />
      <Card className="mb-6 gap-4 border-[#D7E5D8] bg-mint p-5 sm:p-6">
        <View className="h-11 w-11 items-center justify-center rounded-xl bg-white">
          <Camera size={21} color="#23664D" />
        </View>
        <View className="gap-2">
          <Text className="text-[19px] font-semibold text-ink">
            Report a site change
          </Text>
          <Text className="max-w-[430px] text-[13px] leading-5 text-muted">
            Photograph the affected area and describe what changed so the office
            can review your request.
          </Text>
        </View>
        <View className="self-start">
          <Button icon={Camera} onPress={() => go("/new")}>
            Capture a change
          </Button>
        </View>
      </Card>
      <View className="mb-5 flex-row flex-wrap gap-3">
        <QueueCount label="With the office" count={inReview} />
        <QueueCount label="Awaiting decision" count={awaiting} />
        <QueueCount
          label="Decisions received"
          count={changes.length - inReview - awaiting}
        />
      </View>
      <RequestSection
        title="My recent submissions"
        changes={changes}
        action="View my submissions"
        onAction={() => go("/requests")}
        emptyTitle="No submissions yet"
        emptyDescription="Your field reports and their current status will appear here."
        showAmount={false}
      />
    </>
  );
}

function OfficeDashboard({ changes }: DashboardProps) {
  const intake = changes
    .filter((change) => change.status === "submitted")
    .sort(
      (a, b) => Number(b.severity === "high") - Number(a.severity === "high"),
    );
  const urgent = intake.filter((change) => change.severity === "high");
  const next = intake[0];
  return (
    <>
      <PageHeading
        title="Office intake"
        description="Triage field submissions and set the proposed cost and schedule for each request."
      />
      <View className="mb-5 flex-row flex-wrap gap-3">
        <QueueCount label="Ready for review" count={intake.length} />
        <QueueCount label="High priority" count={urgent.length} />
        <QueueCount
          label="With the approver"
          count={
            changes.filter((change) => change.status === "awaiting_client")
              .length
          }
        />
      </View>
      <View className="flex-col gap-5 xl:flex-row">
        <View className="min-w-0 flex-1">
          <RequestSection
            title="Review queue"
            changes={intake}
            action="Open office queue"
            onAction={() => go("/requests")}
            emptyTitle="Intake is clear"
            emptyDescription="New field submissions will appear in this queue."
          />
        </View>
        {next && (
          <Card className="w-full gap-3 self-start border-[#E4D9C7] bg-sand p-5 xl:w-[280px]">
            <View className="flex-row items-center gap-2">
              <ClipboardCheck size={17} color="#9F632D" />
              <Text className="text-[12px] font-semibold text-ochre">
                Next for review
              </Text>
            </View>
            <Text className="text-[17px] font-semibold text-ink">
              {next.title}
            </Text>
            <PriorityBadge high={next.severity === "high"} />
            <Button
              variant="secondary"
              icon={ArrowRight}
              onPress={() => openChange(next.id)}
            >
              Review next request
            </Button>
          </Card>
        )}
      </View>
    </>
  );
}

function ApproverDashboard({ changes }: DashboardProps) {
  const pending = changes.filter((change) => change.status === "awaiting_client");
  const completed = changes
    .filter(
      (change) => change.status === "approved" || change.status === "rejected",
    )
    .sort(
      (a, b) =>
        Date.parse(b.history.at(-1)?.time ?? b.createdAt) -
        Date.parse(a.history.at(-1)?.time ?? a.createdAt),
    );
  return (
    <>
      <PageHeading
        title="Approval desk"
        description="Review the proposed scope, cost, and schedule impact before making a decision."
      />
      <View className="mb-6">
        <SectionTitle
          title="Ready for your decision"
          action="Open approval queue"
          onAction={() => go("/requests")}
        />
        {pending.length === 0 ? (
          <Card>
            <EmptyState
              title="No decisions waiting"
              description="Proposals sent for your approval will appear here."
            />
          </Card>
        ) : (
          <View className="flex-row flex-wrap gap-3">
            {pending.slice(0, 4).map((change) => (
              <Card key={change.id} className="min-w-[240px] flex-1 gap-4 p-5">
                <View className="gap-1">
                  <Text className="text-[11px] text-muted">
                    {getProject(change.projectId).name} · {change.code}
                  </Text>
                  <Text
                    accessibilityRole="header"
                    className="text-[16px] font-semibold text-ink"
                  >
                    {change.title}
                  </Text>
                </View>
                <View className="flex-row flex-wrap gap-x-5 gap-y-3 border-y border-line py-3">
                  <View className="gap-1">
                    <Text className="text-[11px] text-muted">Proposed cost</Text>
                    <Text className="text-[17px] font-semibold text-ink">
                      {money(change.amount)}
                    </Text>
                  </View>
                  <View className="gap-1">
                    <Text className="text-[11px] text-muted">Schedule impact</Text>
                    <Text className="text-[17px] font-semibold text-ink">
                      {change.impactDays === 0
                        ? "No extension"
                        : `+${change.impactDays} ${change.impactDays === 1 ? "day" : "days"}`}
                    </Text>
                  </View>
                </View>
                <Button
                  variant="secondary"
                  icon={ArrowRight}
                  onPress={() => openChange(change.id)}
                >
                  Review proposal
                </Button>
              </Card>
            ))}
          </View>
        )}
      </View>
      <RequestSection
        title="Recent decisions"
        changes={completed}
        action="View decision history"
        onAction={() => go("/requests?status=decided")}
        emptyTitle="No completed decisions"
        emptyDescription="Approved and declined proposals will appear here."
      />
    </>
  );
}

const dashboards = {
  contractor: ContractorDashboard,
  subcontractor: SubcontractorDashboard,
  office: OfficeDashboard,
  approver: ApproverDashboard,
};

export function OverviewScreen() {
  const { changes, role } = useWorkspace();
  const Dashboard = dashboards[role];
  return (
    <AppShell title="Overview">
      <Dashboard changes={changes} />
    </AppShell>
  );
}

function QueueCount({ label, count }: { label: string; count: number }) {
  return (
    <Card className="min-w-[115px] flex-1 gap-1.5 p-4">
      <Text className="text-[23px] font-semibold text-ink">{count}</Text>
      <Text className="text-[11px] font-medium text-muted">{label}</Text>
    </Card>
  );
}

function RequestSection({
  title,
  changes,
  action,
  onAction,
  emptyTitle,
  emptyDescription,
  showAmount = true,
}: {
  title: string;
  changes: WorkspaceChange[];
  action: string;
  onAction: () => void;
  emptyTitle: string;
  emptyDescription: string;
  showAmount?: boolean;
}) {
  return (
    <Card className="overflow-hidden">
      <View className="px-5 pt-5">
        <SectionTitle title={title} action={action} onAction={onAction} />
      </View>
      {changes.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        changes.slice(0, 5).map((change) => (
          <RequestRow
            key={change.id}
            change={change}
            showAmount={showAmount}
            onPress={() => openChange(change.id)}
          />
        ))
      )}
    </Card>
  );
}
