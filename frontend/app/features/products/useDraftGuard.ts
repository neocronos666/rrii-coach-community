import { provideDraftGuard as provide } from "../shared/useDraftGuard";
import { productMessages as p } from "~/i18n/products";
export { useDraftGuard } from "../shared/useDraftGuard";
export function provideDraftGuard() {
  return provide(p.unsaved);
}
