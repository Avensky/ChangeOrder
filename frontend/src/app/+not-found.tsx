import { Text, View } from "react-native";
import { go } from "@/features/workspace/shell";
import { Button, Card } from "@/features/workspace/ui";

// Public error pages must also render without a signed-in workspace provider.
export default function NotFound() {
  return <View className="flex-1 items-center justify-center p-6">
    <Card className="w-full max-w-[440px] gap-4 p-6">
      <Text accessibilityRole="header" className="text-[22px] font-bold text-ink">Page not found</Text>
      <Text className="text-[13px] text-muted">Check the address or return to your workspace.</Text>
      <Button onPress={() => go("/")}>Back to overview</Button>
    </Card>
  </View>;
}
