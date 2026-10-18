import {
  defaultDashboard,
  readDashboard,
  dashboardKey,
  moveBlock,
  moveVisibleBlock,
  supportsSummary,
  type BlockPreference,
} from "./preferences";
import type { BlockId } from "./blocks";
export function useDashboardPreferences() {
  const preferences = useState("dashboard-preferences", defaultDashboard);
  const loaded = useState("dashboard-loaded", () => false);
  const persistent = useState("dashboard-persistent", () => true);
  onMounted(() => {
    if (loaded.value) return;
    try {
      preferences.value = readDashboard(localStorage);
    } catch {
      persistent.value = false;
    }
    loaded.value = true;
  });
  function save() {
    try {
      localStorage.setItem(dashboardKey, JSON.stringify(preferences.value));
      persistent.value = true;
    } catch {
      persistent.value = false;
    }
  }
  function update(id: BlockId, patch: Partial<Omit<BlockPreference, "id">>) {
    preferences.value = {
      version: 1,
      blocks: preferences.value.blocks.map((block) =>
        block.id === id
          ? {
              ...block,
              ...patch,
              view: supportsSummary(id) ? (patch.view ?? block.view) : "list",
            }
          : block,
      ),
    };
    save();
  }
  function move(id: BlockId, offset: -1 | 1) {
    preferences.value = moveBlock(preferences.value, id, offset);
    save();
  }
  function moveVisible(id: BlockId, offset: -1 | 1) {
    preferences.value = moveVisibleBlock(preferences.value, id, offset);
    save();
  }
  function reset() {
    preferences.value = defaultDashboard();
    save();
  }
  return {
    preferences,
    persistent,
    update,
    move,
    moveVisible,
    reset,
    visibleBlocks: computed(() =>
      preferences.value.blocks.filter((block) => block.visible),
    ),
  };
}
