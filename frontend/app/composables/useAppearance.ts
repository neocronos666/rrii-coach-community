import { readAppearance, saveAppearance, type Appearance } from "~/theme/skin";
export function useAppearance() {
  const colorMode = useColorMode();
  const mode = useState<Appearance>("appearance", () => "dark");
  function setMode(value: Appearance) {
    mode.value = value;
    colorMode.preference = value;
    try {
      saveAppearance(window.localStorage, value);
    } catch {
      /* Storage bloqueado. */
    }
  }
  onMounted(() => {
    try {
      setMode(readAppearance(window.localStorage));
    } catch {
      setMode("dark");
    }
  });
  return {
    mode,
    setMode,
    toggle: () => setMode(mode.value === "dark" ? "light" : "dark"),
  };
}
