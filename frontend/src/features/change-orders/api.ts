import { File } from "expo-file-system";
import type { ImagePickerAsset } from "expo-image-picker";
import { Platform } from "react-native";

import { requestJson } from "@/lib/api";

import type { ChangeOrder, Severity } from "./types";

export function submitChange(
  description: string,
  severity: Severity,
  photos: ImagePickerAsset[],
  metadata: { title: string; projectId: string; submittedBy: string },
) {
  const form = new FormData();
  form.append("description", description.trim());
  form.append("severity", severity);

  form.append("title", metadata.title.trim());
  form.append("project_id", metadata.projectId);
  form.append("submitted_by", metadata.submittedBy);
  for (const photo of photos) {
    if (Platform.OS === "web") {
      if (!photo.file)
        throw new Error("Choose the image again before sending.");
      form.append("photos", photo.file, photo.file.name);
    } else {
      // Expo 57's fetch needs a readable File/Blob, not the older RN URI object.
      // File reads the selected photo and supplies its filename and MIME type.
      form.append("photos", new File(photo.uri));
    }
  }

  // fetch supplies the multipart boundary; do not set Content-Type manually.
  return requestJson<ChangeOrder>(
    "/api/v1/changes",
    { method: "POST", body: form },
    30000,
  );
}
