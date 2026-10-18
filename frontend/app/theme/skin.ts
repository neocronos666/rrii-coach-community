export type DisplayProfile = "desktop" | "mobile" | "touch";
export interface Skin {
  id: string;
  profiles: Partial<Record<DisplayProfile, { target: number; gap: number }>>;
}
export const baseSkin: Skin = {
  id: "base",
  profiles: {
    desktop: { target: 44, gap: 16 },
    mobile: { target: 44, gap: 16 },
    touch: { target: 52, gap: 24 },
  },
};
export const nebula: Skin = { id: "nebula", profiles: {} };
export function resolveProfile(skin: Skin, profile: DisplayProfile) {
  return (
    skin.profiles[profile] ??
    baseSkin.profiles[profile] ??
    baseSkin.profiles.desktop!
  );
}
export type Appearance = "dark" | "light";
export const appearanceKey = "rrii-coach.appearance.v1";
export function readAppearance(storage: Pick<Storage, "getItem">): Appearance {
  try {
    return storage.getItem(appearanceKey) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}
export function saveAppearance(
  storage: Pick<Storage, "setItem">,
  value: Appearance,
) {
  try {
    storage.setItem(appearanceKey, value);
  } catch {
    /* Preferencia en memoria. */
  }
}
