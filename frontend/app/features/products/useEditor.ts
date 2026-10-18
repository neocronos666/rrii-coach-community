import { errorMessage } from "../shared/http";
import { productMessages as p } from "~/i18n/products";
export function useEditor() {
  const busy = ref(false),
    failure = ref(""),
    success = ref("");
  async function act(action: () => Promise<void>) {
    busy.value = true;
    failure.value = "";
    success.value = "";
    try {
      await action();
      success.value = p.saved;
    } catch (error) {
      failure.value = errorMessage(error);
    } finally {
      busy.value = false;
    }
  }
  return { busy, failure, success, act };
}
