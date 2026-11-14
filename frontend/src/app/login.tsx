import { useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";
import { useSession } from "@/features/auth/session";
import { Button, Card } from "@/features/workspace/ui";

export default function LoginScreen() {
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    if (busy || !email.trim() || !password) return;
    setBusy(true); setError("");
    try { await signIn(email, password); setPassword(""); }
    catch (cause) { setPassword(""); setError(cause instanceof Error ? cause.message : "Could not sign in."); }
    finally { setBusy(false); }
  }
  return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 24 }}>
    <View className="w-full max-w-[440px] self-center">
      <Card className="gap-4 p-6">
        <Text accessibilityRole="header" className="text-[26px] font-bold text-ink">Staff sign-in</Text>
        <Text className="text-[13px] leading-6 text-muted">Sign in to your field, estimator or manager workspace. The GC uses the emailed approval link.</Text>
        <TextInput accessibilityLabel="Email" placeholder="Email" value={email} onChangeText={setEmail} autoCapitalize="none" autoCorrect={false} keyboardType="email-address" autoComplete="email" editable={!busy} className="min-h-[48px] rounded-xl border border-line p-3 text-ink" />
        <TextInput accessibilityLabel="Password" placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" editable={!busy} onSubmitEditing={submit} className="min-h-[48px] rounded-xl border border-line p-3 text-ink" />
        {!!error && <Text accessibilityRole="alert" className="text-red-700">{error}</Text>}
        <Button busy={busy} disabled={!email.trim() || !password} onPress={submit}>Sign in</Button>
      </Card>
    </View>
  </ScrollView>;
}
