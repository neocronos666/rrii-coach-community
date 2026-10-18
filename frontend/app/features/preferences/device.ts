import { z } from "zod";
export const deviceKey = "rrii-coach.device.v1";
export const deviceSchema = z.object({
  version: z.literal(1),
  profile: z.enum(["auto", "desktop", "mobile", "touch"]),
  density: z.enum(["comfortable", "compact"]),
});
export type DevicePreferences = z.infer<typeof deviceSchema>;
export const defaultDevice: DevicePreferences = {
  version: 1,
  profile: "auto",
  density: "comfortable",
};
export function readDevice(
  storage: Pick<Storage, "getItem">,
): DevicePreferences {
  try {
    const parsed = deviceSchema.safeParse(
      JSON.parse(storage.getItem(deviceKey) ?? "null"),
    );
    return parsed.success ? parsed.data : { ...defaultDevice };
  } catch {
    return { ...defaultDevice };
  }
}
export function saveDevice(
  storage: Pick<Storage, "setItem">,
  value: DevicePreferences,
): boolean {
  try {
    storage.setItem(deviceKey, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
export function resolveDisplay(
  profile: DevicePreferences["profile"],
  narrow: boolean,
  coarse: boolean,
) {
  return profile === "auto"
    ? narrow
      ? "mobile"
      : coarse
        ? "touch"
        : "desktop"
    : profile;
}
