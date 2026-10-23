import { CheckCheck, ChevronRight } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { useWorkspace } from "./context";
import { shortDate } from "./data";
import { AppShell, openChange } from "./shell";
import { Avatar, Button, Card, PageHeading } from "./ui";

export function ActivityScreen() {
  const { changes, events, unread, markRead } = useWorkspace();
  return (
    <AppShell title="Activity">
      <PageHeading
        eyebrow="NOTHING LOST IN THE BACK-AND-FORTH"
        title="Activity"
        description="A shared record of submissions, reviews, and decisions."
        action={
          <Button
            icon={CheckCheck}
            variant="secondary"
            onPress={markRead}
            disabled={!unread}
          >
            Mark all as read
          </Button>
        }
      />
      <View className="mb-5 flex-row items-center gap-2">
        <Text className="text-[12px] font-semibold text-ink">
          Workspace updates
        </Text>
        {unread > 0 && (
          <View className="rounded-full bg-mint px-2 py-1">
            <Text className="text-[9px] font-semibold text-forest">
              {unread} new
            </Text>
          </View>
        )}
        <Text className="ml-auto text-[10px] text-muted">In-app activity</Text>
      </View>
      <Card className="overflow-hidden">
        {events.map((event, i) => {
          const change = changes.find((item) => item.id === event.changeId);
          return (
            <Pressable
              key={event.id}
              accessibilityRole="button"
              onPress={() => openChange(event.changeId)}
              className={`flex-row items-start gap-3 px-5 py-5 hover:bg-canvas ${i ? "border-t border-line" : ""}`}
            >
              <Avatar name={event.person} size={37} />
              <View className="min-w-0 flex-1">
                <Text className="text-[12px] font-semibold text-ink">
                  {event.title}
                </Text>
                <Text className="mt-1.5 text-[11px] leading-5 text-muted">
                  {change?.code} · {change?.title}
                </Text>
                <Text className="mt-2 text-[10px] text-muted">
                  {event.person} · {shortDate(event.time)}
                </Text>
              </View>
              {i < unread && (
                <View className="mt-2 h-1.5 w-1.5 rounded-full bg-forest" />
              )}
              <ChevronRight size={14} color="#99AA9C" />
            </Pressable>
          );
        })}
      </Card>
    </AppShell>
  );
}
