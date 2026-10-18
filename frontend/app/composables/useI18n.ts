import { es, type MessageKey } from "~/i18n/es";
// Catálogo tipado inicial. La resolución queda centralizada para futuros idiomas.
export function useI18n() {
  return { t: (key: MessageKey): string => es[key] };
}
