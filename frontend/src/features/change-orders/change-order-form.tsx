import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import {
  ArrowLeft,
  ArrowRight,
  Camera,
  Check,
  CheckCircle2,
  ImagePlus,
  Lightbulb,
  Radio,
  X,
} from "lucide-react-native";
import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import { useWorkspace } from "@/features/workspace/context";
import { getProject, projects } from "@/features/workspace/data";
import { go, openChange } from "@/features/workspace/shell";
import {
  Button,
  Card,
  PageHeading,
  PriorityBadge,
  SectionTitle,
} from "@/features/workspace/ui";

import type { Severity } from "./types";

export function ChangeOrderForm() {
  const { create, mode, setMode } = useWorkspace();
  const [projectId, setProjectId] = useState(projects[0].id);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<Severity>("normal");
  const [photo, setPhoto] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [picking, setPicking] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  const busy = picking || sending;
  const ready = !!title.trim() && !!description.trim() && !!photo;

  async function pickPhoto(source: "camera" | "library") {
    setError("");
    setPicking(true);
    try {
      if (source === "camera" && Platform.OS !== "web") {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted)
          throw new Error(
            "Allow camera access in Settings, or choose an existing photo.",
          );
      }
      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ["images"],
        quality: 0.7,
        allowsEditing: false,
      };
      const result = await (source === "camera"
        ? ImagePicker.launchCameraAsync(options)
        : ImagePicker.launchImageLibraryAsync(options));
      if (!result.canceled) {
        const selected = result.assets[0];
        if (selected.fileSize && selected.fileSize > 10 * 1024 * 1024)
          throw new Error("Choose an image that is 10 MB or smaller.");
        setPhoto(selected);
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not open the photo picker.",
      );
    } finally {
      setPicking(false);
    }
  }

  async function send() {
    if (submitting.current) return;
    setError("");
    if (!ready || !photo) {
      setError("Add a title, short description, and one photo before sending.");
      return;
    }
    submitting.current = true;
    setSending(true);
    try {
      const change = await create({
        title,
        description,
        severity,
        projectId,
        photo,
      });
      setTitle("");
      setDescription("");
      setSeverity("normal");
      setPhoto(null);
      openChange(change.id);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "The change could not be sent.",
      );
    } finally {
      submitting.current = false;
      setSending(false);
    }
  }

  return (
    <>
      <Pressable
        accessibilityRole="button"
        onPress={() => go("/requests")}
        className="mb-5 flex-row items-center gap-2 self-start"
      >
        <ArrowLeft size={14} color="#74827C" />
        <Text className="text-[11px] text-muted">Back to requests</Text>
      </Pressable>
      <PageHeading
        eyebrow="CAPTURE IT WHILE IT'S FRESH"
        title="A change starts here."
        description="One photo. A few details. Your office can take it from here."
      />
      <View className="mb-6 flex-row items-center gap-3 px-1">
        {["Capture the change", "Office review", "Client approval"].map(
          (step, i) => (
            <View key={step} className="flex-1 flex-row items-center gap-2">
              <View
                className={`h-6 w-6 items-center justify-center rounded-full ${i === 0 ? "bg-forest" : "bg-[#E6EBE3]"}`}
              >
                <Text
                  className={`text-[10px] font-semibold ${i === 0 ? "text-white" : "text-muted"}`}
                >
                  {i + 1}
                </Text>
              </View>
              <Text
                className={`flex-1 text-[10px] ${i === 0 ? "font-semibold text-ink" : "text-muted"}`}
              >
                {step}
              </Text>
              {i < 2 && <ArrowRight size={12} color="#AFBDB0" />}
            </View>
          ),
        )}
      </View>

      <View className="flex-col gap-5 lg:flex-row">
        <View className="min-w-0 flex-1">
          <Card className="gap-6 p-5 lg:p-7">
            <View>
              <SectionTitle title="Project" />
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View className="flex-row gap-2">
                  {projects.map((project) => (
                    <Pressable
                      key={project.id}
                      accessibilityRole="button"
                      accessibilityLabel={"Select project: " + project.name}
                      disabled={busy}
                      onPress={() => setProjectId(project.id)}
                      className={`min-w-[150px] flex-1 gap-2 rounded-xl border p-3 ${projectId === project.id ? "border-forest bg-mint" : "border-line bg-white"}`}
                    >
                      <View className="flex-row items-center justify-between">
                        <Text className="text-[10px] font-bold text-forest">
                          {project.initials}
                        </Text>
                        {projectId === project.id && (
                          <Check size={12} color="#23664D" />
                        )}
                      </View>
                      <Text className="text-[11px] font-semibold text-ink">
                        {project.name}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </ScrollView>
            </View>
            <View>
              <Text className="mb-2 text-[12px] font-semibold text-ink">
                Change title <Text className="text-forest">*</Text>
              </Text>
              <TextInput
                accessibilityLabel="Change title"
                placeholder="e.g. Kitchen outlet relocation"
                placeholderTextColor="#8B9B90"
                value={title}
                onChangeText={setTitle}
                maxLength={80}
                editable={!busy}
                className="min-h-[48px] rounded-xl border border-line bg-[#FCFCFA] px-4 text-[13px] text-ink focus:border-forest"
              />
            </View>
            <View>
              <View className="mb-2 flex-row items-center justify-between">
                <Text className="text-[12px] font-semibold text-ink">
                  What changed? <Text className="text-forest">*</Text>
                </Text>
                <Text className="text-[10px] text-muted">
                  {description.length}/500
                </Text>
              </View>
              <TextInput
                accessibilityLabel="Change description"
                placeholder="Describe the change and why it is needed. A little context helps the office move faster."
                placeholderTextColor="#8B9B90"
                value={description}
                onChangeText={setDescription}
                maxLength={500}
                multiline
                editable={!busy}
                textAlignVertical="top"
                className="min-h-[130px] rounded-xl border border-line bg-[#FCFCFA] p-4 text-[13px] leading-6 text-ink focus:border-forest"
              />
            </View>
            <View>
              <Text className="mb-3 text-[12px] font-semibold text-ink">
                Priority
              </Text>
              <View accessibilityRole="radiogroup" className="flex-row gap-3">
                {(["normal", "high"] as const).map((value) => (
                  <Pressable
                    key={value}
                    accessibilityRole="radio"
                    accessibilityLabel={value + " priority"}
                    accessibilityState={{
                      checked: severity === value,
                      disabled: busy,
                    }}
                    disabled={busy}
                    onPress={() => setSeverity(value)}
                    className={`min-h-[80px] flex-1 rounded-xl border p-3 ${severity === value ? (value === "high" ? "border-orange-300 bg-orange-50" : "border-forest bg-mint") : "border-line bg-white"}`}
                  >
                    <View className="mb-2 flex-row items-center justify-between">
                      <PriorityBadge high={value === "high"} />
                      <View
                        className={`h-4 w-4 items-center justify-center rounded-full border ${severity === value ? "border-forest bg-forest" : "border-[#CFD9CF]"}`}
                      >
                        {severity === value && (
                          <Check size={10} color="white" />
                        )}
                      </View>
                    </View>
                    <Text className="text-[10px] text-muted">
                      {value === "normal"
                        ? "Standard review"
                        : "Needs prompt attention"}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
            <View>
              <View className="mb-3 flex-row items-center justify-between">
                <Text className="text-[12px] font-semibold text-ink">
                  Site photo <Text className="text-forest">*</Text>
                </Text>
                <Text className="text-[10px] text-muted">
                  One photo · up to 10 MB
                </Text>
              </View>
              {photo ? (
                <View className="relative mb-3 overflow-hidden rounded-xl border border-line bg-canvas">
                  <Image
                    source={{ uri: photo.uri }}
                    style={{ width: "100%", height: 250 }}
                    contentFit="contain"
                    accessibilityLabel="Selected site photo"
                  />
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Remove photo"
                    disabled={busy}
                    onPress={() => setPhoto(null)}
                    className="absolute right-3 top-3 rounded-full bg-white p-2"
                  >
                    <X size={15} color="#23664D" />
                  </Pressable>
                  <View className="flex-row items-center gap-1.5 border-t border-line bg-white px-3 py-2">
                    <CheckCircle2 size={12} color="#23664D" />
                    <Text className="text-[10px] text-muted">
                      Photo attached and ready
                    </Text>
                  </View>
                </View>
              ) : (
                <View className="mb-3 items-center gap-2 rounded-xl border border-dashed border-[#C5D5C2] bg-[#F7FAF4] px-5 py-7">
                  <View className="mb-1 h-10 w-10 items-center justify-center rounded-xl bg-[#E7EFDF]">
                    <Camera size={20} color="#69865F" strokeWidth={1.5} />
                  </View>
                  <Text className="text-[12px] font-semibold text-ink">
                    Show the office what you see.
                  </Text>
                  <Text className="text-center text-[10px] leading-4 text-muted">
                    A clear photo gives your change the context it needs.
                  </Text>
                </View>
              )}
              <View className="flex-row flex-wrap gap-2">
                <View className="min-w-[120px] flex-1">
                  <Button
                    variant="secondary"
                    icon={Camera}
                    disabled={busy}
                    onPress={() => pickPhoto("camera")}
                  >
                    {photo ? "Retake photo" : "Take photo"}
                  </Button>
                </View>
                <View className="min-w-[120px] flex-1">
                  <Button
                    variant="secondary"
                    icon={ImagePlus}
                    disabled={busy}
                    onPress={() => pickPhoto("library")}
                  >
                    Choose photo
                  </Button>
                </View>
              </View>
              {picking && (
                <ActivityIndicator
                  className="mt-3"
                  color="#23664D"
                  accessibilityLabel="Opening photo picker"
                />
              )}
            </View>
            {!!error && (
              <Text
                accessibilityRole="alert"
                className="rounded-xl border border-red-100 bg-red-50 p-3 text-[12px] leading-5 text-red-700"
              >
                {error}
              </Text>
            )}
            <View className="gap-3 border-t border-line pt-5">
              <Button
                icon={ArrowRight}
                disabled={!ready || picking}
                busy={sending}
                onPress={send}
              >
                Send to office
              </Button>
              <Text className="text-center text-[10px] leading-4 text-muted">
                {mode === "demo"
                  ? "Demo submission · saved in this workspace for the walkthrough"
                  : "Connected submission · uploads the photo and description to your server"}
              </Text>
            </View>
          </Card>
        </View>
        <View className="w-full gap-5 lg:w-[292px]">
          <Card className="p-5">
            <SectionTitle title="Request at a glance" />
            <Text className="mb-1 text-[10px] text-muted">Project</Text>
            <Text className="mb-5 text-[12px] font-semibold text-ink">
              {getProject(projectId).name}
            </Text>
            <Text className="mb-2 text-[10px] text-muted">Priority</Text>
            <PriorityBadge high={severity === "high"} />
            <View className="my-4 h-px bg-line" />
            <View className="gap-3">
              {[
                { label: "Clear title", ready: !!title.trim() },
                { label: "Short description", ready: !!description.trim() },
                { label: "Site photo", ready: !!photo },
              ].map((item) => (
                <View key={item.label} className="flex-row items-center gap-2">
                  <View
                    className={`h-4 w-4 items-center justify-center rounded-full ${item.ready ? "bg-mint" : "bg-canvas"}`}
                  >
                    <Check
                      size={10}
                      color={item.ready ? "#23664D" : "#C4CEC1"}
                    />
                  </View>
                  <Text className="text-[11px] text-muted">{item.label}</Text>
                </View>
              ))}
            </View>
          </Card>
          <View className="rounded-card border border-[#E6DDCB] bg-[#F8F3E8] p-5">
            <Lightbulb size={21} color="#AE8A4C" strokeWidth={1.5} />
            <Text className="mb-2 mt-3 text-[13px] font-semibold text-ink">
              A little detail goes a long way.
            </Text>
            <Text className="text-[11px] leading-5 text-[#8E8168]">
              Include what changed, where it is, and why it is needed. The
              office can add cost and schedule details during review.
            </Text>
          </View>
          <Card className="p-5">
            <View className="mb-3 flex-row items-center gap-2">
              <Radio size={15} color="#23664D" />
              <Text className="text-[12px] font-semibold text-ink">
                Submission mode
              </Text>
            </View>
            <Text className="mb-3 text-[11px] leading-5 text-muted">
              {mode === "demo"
                ? "Explore the full workflow with local sample data."
                : "Your working photo upload is enabled. The API must be running."}
            </Text>
            <Button
              variant="quiet"
              small
              disabled={busy}
              onPress={() => setMode(mode === "demo" ? "connected" : "demo")}
            >
              {mode === "demo" ? "Use connected upload" : "Switch to demo mode"}
            </Button>
          </Card>
        </View>
      </View>
    </>
  );
}
