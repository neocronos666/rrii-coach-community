import { ApiError } from "./http";
import {
  readPending,
  savePending,
  newRequestId,
  type MutationRequest,
} from "./pending";
import { errorMessage } from "./http";
import { requestMessages as q } from "~/i18n/requests";
export function usePending<T extends MutationRequest, R>(
  scope: string,
  send: (body: T) => Promise<R>,
  namespace = "quick-quote",
) {
  const key = `rrii-coach.${namespace}.pending.v1:${useRuntimeConfig().public.apiBaseUrl}:${scope}`;
  const pending = shallowRef<T | null>(null),
    busy = ref(false),
    error = ref(""),
    persistent = ref(true),
    invalid = ref(false),
    ready = ref(false);
  onMounted(() => {
    let raw: string | null = null;
    try {
      raw = sessionStorage.getItem(key);
    } catch {
      persistent.value = false;
    }
    try {
      pending.value = readPending<T>({ getItem: () => raw }, key);
    } catch {
      invalid.value = true;
    }
    ready.value = true;
  });
  function clear() {
    pending.value = null;
    try {
      sessionStorage.removeItem(key);
    } catch {
      persistent.value = false;
    }
  }
  function clearInvalid() {
    try {
      sessionStorage.removeItem(key);
      invalid.value = false;
    } catch {
      error.value = q.invalidPending;
    }
  }
  async function run(input?: Omit<T, "request_id">): Promise<R | undefined> {
    if (busy.value || !ready.value || invalid.value) return;
    error.value = "";
    if (!pending.value) {
      if (!input) return;
      pending.value = {
        ...JSON.parse(JSON.stringify(input)),
        request_id: newRequestId(),
      } as T;
      try {
        savePending(sessionStorage, key, pending.value);
      } catch {
        persistent.value = false;
      }
    }
    busy.value = true;
    try {
      const response = await send(pending.value);
      clear();
      return response;
    } catch (reason) {
      error.value = errorMessage(reason);
      if (
        reason instanceof ApiError &&
        reason.status >= 400 &&
        reason.status !== 408 &&
        reason.status < 500
      )
        clear();
      return undefined;
    } finally {
      busy.value = false;
    }
  }
  return {
    pending,
    busy,
    error,
    persistent,
    invalid,
    ready,
    run,
    clearInvalid,
  };
}
