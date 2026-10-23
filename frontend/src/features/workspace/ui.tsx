import {
  ArrowRight,
  Check,
  ChevronRight,
  FileText,
  type LucideIcon,
} from "lucide-react-native";
import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import Svg, { Circle, Line, Path, Rect } from "react-native-svg";

import {
  type ChangeStatus,
  type WorkspaceChange,
  getProject,
  money,
  shortDate,
  statusLabels,
} from "./data";

export function Button({
  children,
  onPress,
  variant = "primary",
  icon: Icon,
  disabled,
  busy,
  small,
}: {
  children: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "quiet" | "danger";
  icon?: LucideIcon;
  disabled?: boolean;
  busy?: boolean;
  small?: boolean;
}) {
  const background = {
    primary: "bg-forest hover:bg-forest-dark",
    secondary: "border border-line bg-white hover:bg-canvas",
    quiet: "bg-transparent hover:bg-mint",
    danger: "border border-red-200 bg-red-50 hover:bg-red-100",
  }[variant];
  const color =
    variant === "primary"
      ? "#FFFFFF"
      : variant === "danger"
        ? "#B54742"
        : "#23664D";
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={children}
      disabled={disabled || busy}
      onPress={onPress}
      className={`${background} ${small ? "min-h-[36px] px-3 py-2" : "min-h-[46px] px-5 py-3"} ${disabled || busy ? "opacity-50" : "active:opacity-75"} flex-row items-center justify-center gap-2 rounded-xl`}
    >
      {busy ? (
        <ActivityIndicator size="small" color={color} />
      ) : Icon ? (
        <Icon size={16} color={color} strokeWidth={1.8} />
      ) : null}
      <Text
        className={`text-[13px] font-semibold ${variant === "primary" ? "text-white" : variant === "danger" ? "text-red-700" : "text-forest"}`}
      >
        {children}
      </Text>
    </Pressable>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <View className={`rounded-card border border-line bg-white ${className}`}>
      {children}
    </View>
  );
}

const statusClasses: Record<ChangeStatus, { box: string; text: string }> = {
  submitted: { box: "bg-slate-100", text: "text-slate-600" },
  awaiting_client: { box: "bg-amber-50", text: "text-amber-800" },
  approved: { box: "bg-emerald-50", text: "text-emerald-800" },
  rejected: { box: "bg-rose-50", text: "text-rose-700" },
};

export function StatusBadge({ status }: { status: ChangeStatus }) {
  const colors = statusClasses[status];
  return (
    <View
      className={`self-start flex-row items-center gap-1.5 rounded-full px-2.5 py-1.5 ${colors.box}`}
    >
      {status === "approved" ? (
        <Check size={11} color="#166534" />
      ) : (
        <View
          className={`h-1.5 w-1.5 rounded-full ${status === "awaiting_client" ? "bg-amber-500" : status === "rejected" ? "bg-rose-400" : "bg-slate-400"}`}
        />
      )}
      <Text className={`text-[10px] font-semibold ${colors.text}`}>
        {statusLabels[status]}
      </Text>
    </View>
  );
}

export function PriorityBadge({ high }: { high: boolean }) {
  return (
    <View className="flex-row items-center gap-1.5">
      <View
        className={`h-1.5 w-1.5 rounded-full ${high ? "bg-orange-500" : "bg-emerald-500"}`}
      />
      <Text
        className={`text-[11px] ${high ? "font-semibold text-amber-800" : "text-muted"}`}
      >
        {high ? "High priority" : "Normal"}
      </Text>
    </View>
  );
}

export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
  return (
    <View
      className="items-center justify-center rounded-full border border-white bg-mint"
      style={{ width: size, height: size }}
    >
      <Text className="text-[10px] font-bold text-forest">{initials}</Text>
    </View>
  );
}

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <View className="mb-6 flex-row flex-wrap items-end justify-between gap-4">
      <View className="min-w-[180px] flex-1 gap-2">
        {eyebrow && (
          <Text className="text-[10px] font-semibold uppercase tracking-[2px] text-muted">
            {eyebrow}
          </Text>
        )}
        <Text
          accessibilityRole="header"
          className="text-[28px] font-bold leading-9 tracking-[-0.8px] text-ink"
        >
          {title}
        </Text>
        {description && (
          <Text className="text-[13px] leading-5 text-muted">
            {description}
          </Text>
        )}
      </View>
      {action}
    </View>
  );
}

export function SectionTitle({
  title,
  action,
  onAction,
}: {
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <View className="mb-5 flex-row items-center justify-between gap-3">
      <Text className="text-[15px] font-semibold text-ink">{title}</Text>
      {action && onAction && (
        <Pressable
          accessibilityRole="button"
          onPress={onAction}
          className="min-h-[32px] flex-row items-center gap-1"
        >
          <Text className="text-[11px] font-semibold text-forest">
            {action}
          </Text>
          <ChevronRight size={13} color="#23664D" />
        </Pressable>
      )}
    </View>
  );
}

export function RequestRow({
  change,
  onPress,
  compact = false,
}: {
  change: WorkspaceChange;
  onPress: () => void;
  compact?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open ${change.code}: ${change.title}`}
      onPress={onPress}
      className="min-h-[88px] flex-row items-center gap-3 border-t border-line px-5 py-4 hover:bg-canvas active:bg-mint"
    >
      {!compact && (
        <View className="h-10 w-10 items-center justify-center rounded-xl bg-canvas">
          <FileText size={18} color="#547767" strokeWidth={1.6} />
        </View>
      )}
      <View className="min-w-0 flex-1 gap-1.5">
        <Text className="text-[13px] font-semibold text-ink" numberOfLines={1}>
          {change.title}
        </Text>
        <Text className="text-[10px] text-muted" numberOfLines={1}>
          {change.code} <Text className="text-line"> / </Text>{" "}
          {getProject(change.projectId).name}
        </Text>
        <View className="mt-1 flex-row items-center gap-3 md:hidden">
          <StatusBadge status={change.status} />
          <PriorityBadge high={change.severity === "high"} />
        </View>
      </View>
      <View className="hidden w-[138px] md:flex">
        <StatusBadge status={change.status} />
      </View>
      {!compact && (
        <View className="hidden w-[100px] xl:flex">
          <PriorityBadge high={change.severity === "high"} />
        </View>
      )}
      <View className="items-end gap-2">
        <Text className="text-[12px] font-semibold text-ink">
          {change.amount ? money(change.amount) : "To estimate"}
        </Text>
        <Text className="text-[10px] text-muted">
          {shortDate(change.createdAt)}
        </Text>
      </View>
      <ChevronRight size={14} color="#96A29B" />
    </Pressable>
  );
}

export function EmptyState({
  title,
  description,
  onAction,
  action = "New change request",
}: {
  title: string;
  description: string;
  onAction?: () => void;
  action?: string;
}) {
  return (
    <View className="items-center gap-4 px-6 py-12">
      <View className="h-14 w-14 items-center justify-center rounded-2xl bg-mint">
        <FileText size={24} color="#23664D" strokeWidth={1.5} />
      </View>
      <Text className="text-[17px] font-semibold text-ink">{title}</Text>
      <Text className="max-w-[300px] text-center text-[13px] leading-5 text-muted">
        {description}
      </Text>
      {onAction && (
        <Button onPress={onAction} icon={ArrowRight}>
          {action}
        </Button>
      )}
    </View>
  );
}

// A local, code-drawn project illustration keeps the demo available offline.
export function ProjectArt({
  variant = 0,
  height = 140,
}: {
  variant?: number;
  height?: number;
}) {
  const bg = ["#E8EEDC", "#E5EBED", "#F0E6D7"][variant % 3];
  const building = ["#B6C4A8", "#A9BFC6", "#D4BA9C"][variant % 3];
  return (
    <View style={{ height, backgroundColor: bg }} className="overflow-hidden">
      <Svg
        width="100%"
        height="100%"
        viewBox="0 0 440 180"
        preserveAspectRatio="xMidYMid slice"
      >
        <Circle cx="355" cy="45" r="50" fill="#FFFFFF" opacity="0.38" />
        <Path d="M0 149L440 128V180H0Z" fill="#FFFFFF" opacity="0.27" />
        <Path d="M124 81L221 45L331 82L236 120Z" fill="#FDFCF6" />
        <Path d="M124 81L236 120V171L124 131Z" fill={building} />
        <Path d="M236 120L331 82V135L236 171Z" fill="#8FA58F" />
        <Path d="M150 68L221 32L298 58L226 88Z" fill="#738E79" />
        <Path d="M150 68L226 88V119L150 92Z" fill="#D7DFCE" />
        <Path d="M226 88L298 58V91L226 119Z" fill="#A4B69E" />
        <Path d="M253 126L276 117V146L253 156Z" fill="#D8E7DB" />
        <Path d="M291 111L314 102V130L291 140Z" fill="#D8E7DB" />
        <Path d="M143 98L164 106V129L143 121Z" fill="#ECF1E5" />
        <Path d="M179 111L216 125V148L179 135Z" fill="#ECF1E5" />
        <Line
          x1="81"
          y1="108"
          x2="81"
          y2="157"
          stroke="#8CA27F"
          strokeWidth="4"
        />
        <Circle cx="81" cy="102" r="19" fill="#A4B98E" />
        <Circle cx="369" cy="134" r="13" fill="#A4B98E" />
        <Rect
          x="63"
          y="159"
          width="315"
          height="2"
          fill="#748B75"
          opacity="0.2"
        />
      </Svg>
    </View>
  );
}
