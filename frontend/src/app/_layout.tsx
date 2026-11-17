import "@/global.css";

import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider, useSession } from "@/features/auth/session";
import { WorkspaceProvider } from "@/features/workspace/context";

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
  return <SessionProvider><AuthenticatedLayout /></SessionProvider>;
}

function AuthenticatedLayout() {
  const { user } = useSession();
  useEffect(() => { void SplashScreen.hideAsync(); }, []);
  const screens = <>
    <StatusBar style="dark" />
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "#F5F6F3" }, animation: "fade" }}>
      <Stack.Protected guard={!user}><Stack.Screen name="login" /></Stack.Protected>
      <Stack.Protected guard={!!user}>
        <Stack.Screen name="index" />
        <Stack.Screen name="requests" />
        <Stack.Screen name="changes/[id]" />
        <Stack.Screen name="projects" />
        <Stack.Screen name="activity" />
        <Stack.Screen name="settings" />
      </Stack.Protected>
      <Stack.Protected guard={user?.role === "field"}><Stack.Screen name="new" /></Stack.Protected>
      <Stack.Protected guard={!!user && user.role !== "field"}><Stack.Screen name="work-order" /></Stack.Protected>
      <Stack.Screen name="approve" />
      <Stack.Protected guard={false}><Stack.Screen name="explore" /></Stack.Protected>
    </Stack>
  </>;
  return <SafeAreaProvider>
    {user ? <WorkspaceProvider key={user.id}>{screens}</WorkspaceProvider> : screens}
  </SafeAreaProvider>;
}
