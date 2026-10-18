import type { InjectionKey } from "vue";
const draftRegistry: InjectionKey<Map<string, boolean>> =
  Symbol("product-drafts");
export function provideDraftGuard(message: string) {
  const drafts = reactive(new Map<string, boolean>());
  provide(draftRegistry, drafts);
  const dirty = () => [...drafts.values()].some(Boolean);
  onBeforeRouteLeave(() => !dirty() || window.confirm(message));
  function beforeUnload(event: BeforeUnloadEvent) {
    if (dirty()) {
      event.preventDefault();
      event.returnValue = "";
    }
  }
  onMounted(() => window.addEventListener("beforeunload", beforeUnload));
  onBeforeUnmount(() =>
    window.removeEventListener("beforeunload", beforeUnload),
  );
  return drafts;
}
export function useDraftGuard(
  key: string,
  snapshot: () => unknown,
  ownRegistry?: Map<string, boolean>,
) {
  const registry = ownRegistry ?? inject(draftRegistry);
  let saved = JSON.stringify(snapshot());
  const current = computed(() => JSON.stringify(snapshot()));
  watch(current, (value) => registry?.set(key, value !== saved), {
    flush: "sync",
  });
  function markSaved() {
    saved = current.value;
    registry?.set(key, false);
  }
  onBeforeUnmount(() => registry?.delete(key));
  return markSaved;
}
