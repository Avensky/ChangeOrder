import { useState } from "react";
import { Text } from "react-native";
import { useSession } from "@/features/auth/session";
import { checkBackendHealth } from "@/lib/api";
import { AppShell } from "./shell";
import { Button, Card, PageHeading } from "./ui";

export function SettingsScreen() {
  const { user, signOut } = useSession();
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState("");
  return <AppShell title="Account settings">
    <PageHeading title="Your account" description="Your workspace role is verified by the server." />
    <Card className="gap-4 p-5">
      <Text className="text-[16px] font-semibold text-ink">{user?.name}</Text>
      <Text className="text-[13px] text-muted">Signed in as {user?.role}</Text>
      <Button variant="secondary" busy={checking} onPress={async () => {
        setChecking(true);
        try { await checkBackendHealth(); setStatus("Backend: ok"); }
        catch { setStatus("Backend unavailable. Check your connection and try again."); }
        finally { setChecking(false); }
      }}>Check backend</Button>
      {!!status && <Text accessibilityLiveRegion="polite">{status}</Text>}
      <Button onPress={signOut}>Sign out</Button>
      <Text className="text-[12px] leading-5 text-muted">This session is kept in memory. Sign in again after closing or reloading the app, or when the session expires.</Text>
    </Card>
  </AppShell>;
}
