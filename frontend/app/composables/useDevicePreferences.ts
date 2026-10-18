import {
  defaultDevice,
  readDevice,
  saveDevice,
  resolveDisplay,
  type DevicePreferences,
} from "~/features/preferences/device";
import { nebula, resolveProfile } from "~/theme/skin";
export function useDevicePreferences() {
  const preferences = useState<DevicePreferences>("device-preferences", () => ({
    ...defaultDevice,
  }));
  const persistent = useState("device-persistent", () => true);
  const narrow = ref(false);
  const coarse = ref(false);
  const profile = computed(() =>
    resolveDisplay(preferences.value.profile, narrow.value, coarse.value),
  );
  const navigation = computed(() =>
    profile.value === "mobile" || (profile.value === "touch" && narrow.value)
      ? "bottom"
      : "side",
  );
  let cleanup = () => {};
  onMounted(() => {
    try {
      preferences.value = readDevice(window.localStorage);
    } catch {
      persistent.value = false;
    }
    const width = window.matchMedia("(max-width: 767px)");
    const pointer = window.matchMedia("(pointer: coarse)");
    const update = () => {
      narrow.value = width.matches;
      coarse.value = pointer.matches;
    };
    update();
    width.addEventListener("change", update);
    pointer.addEventListener("change", update);
    cleanup = () => {
      width.removeEventListener("change", update);
      pointer.removeEventListener("change", update);
    };
  });
  onBeforeUnmount(() => cleanup());
  function update(patch: Partial<Omit<DevicePreferences, "version">>) {
    preferences.value = { ...preferences.value, ...patch };
    try {
      persistent.value = saveDevice(window.localStorage, preferences.value);
    } catch {
      persistent.value = false;
    }
  }
  const metrics = computed(() => resolveProfile(nebula, profile.value));
  useHead(() => ({
    htmlAttrs: {
      "data-display-profile": profile.value,
      "data-navigation": navigation.value,
      "data-density": preferences.value.density,
      style: `--target: ${metrics.value.target}px; --content-gap: ${metrics.value.gap}px`,
    },
  }));
  return { preferences, persistent, profile, update };
}
