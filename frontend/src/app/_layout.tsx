import "@/global.css";

import { Stack, usePathname } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { WorkspaceProvider } from "@/features/workspace/context";

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
  const pathname = usePathname();
  useEffect(() => {
    void SplashScreen.hideAsync();
  }, []);
  const screens = (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "#F5F6F3" }, animation: "fade" }} />
    </>
  );
  return (
    <SafeAreaProvider>
      {pathname === "/approve" ? screens : <WorkspaceProvider>{screens}</WorkspaceProvider>}
    </SafeAreaProvider>
  );
}
