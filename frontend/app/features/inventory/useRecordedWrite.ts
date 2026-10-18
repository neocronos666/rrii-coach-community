import { ApiError, errorMessage } from "../shared/http";
import { reviewRecord, type ReviewRecord } from "./values";
// No reenvía operaciones sin clave idempotente. Sólo conserva aviso para revisión humana.
export function useRecordedWrite(
  scope: string,
  refresh: () => Promise<boolean>,
) {
  const key = `rrii-coach.inventory.review.v1:${useRuntimeConfig().public.apiBaseUrl}:${scope}`;
  const review = shallowRef<ReviewRecord | null>(null),
    invalid = ref(false),
    busy = ref(false),
    ready = ref(false),
    persistent = ref(true),
    error = ref(""),
    saved = ref(false),
    reviewed = ref(false);
  onMounted(() => {
    try {
      const raw = sessionStorage.getItem(key);
      if (raw !== null) {
        try {
          review.value = reviewRecord.parse(JSON.parse(raw));
        } catch {
          invalid.value = true;
        }
      }
    } catch {
      persistent.value = false;
    }
    ready.value = true;
  });
  function clear() {
    review.value = null;
    invalid.value = false;
    reviewed.value = false;
    try {
      sessionStorage.removeItem(key);
    } catch {
      persistent.value = false;
    }
  }
  async function inspect() {
    try {
      reviewed.value = await refresh();
    } catch {
      reviewed.value = false;
    }
  }
  function acknowledge() {
    if (!busy.value && reviewed.value) {
      clear();
      error.value = "";
      saved.value = false;
    }
  }
  async function run<T>(
    summary: string,
    send: () => Promise<T>,
  ): Promise<T | undefined> {
    if (!ready.value || busy.value || review.value || invalid.value) return;
    busy.value = true;
    saved.value = false;
    reviewed.value = false;
    error.value = "";
    review.value = { version: 1, summary, createdAt: new Date().toISOString() };
    try {
      sessionStorage.setItem(key, JSON.stringify(review.value));
    } catch {
      persistent.value = false;
    }
    try {
      const result = await send();
      clear();
      saved.value = true;
      return result;
    } catch (failure) {
      error.value = errorMessage(failure);
      if (
        failure instanceof ApiError &&
        failure.status >= 400 &&
        failure.status < 500 &&
        failure.status !== 408
      )
        clear();
    } finally {
      await inspect();
      busy.value = false;
    }
  }
  const locked = computed(
    () => !ready.value || busy.value || !!review.value || invalid.value,
  );
  return {
    review,
    invalid,
    busy,
    persistent,
    error,
    saved,
    reviewed,
    locked,
    run,
    inspect,
    acknowledge,
  };
}
