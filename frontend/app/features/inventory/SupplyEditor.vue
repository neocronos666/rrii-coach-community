<script setup lang="ts">
import { inventoryApi, type Schema } from "./api";
import { useRecordedWrite } from "./useRecordedWrite";
import WriteStatus from "./WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import {
  inventoryMessages as i,
  supplyCategories,
  supplyUnits,
} from "~/i18n/inventory";
const props = defineProps<{
  supply?: Schema["SupplyRead"];
  refresh: () => Promise<boolean>;
}>();
const emit = defineEmits<{ saved: [id: string] }>();
const api = inventoryApi(useRuntimeConfig().public.apiBaseUrl);
const body = ref<Schema["SupplyCreate"]>({
  name: props.supply?.name ?? "",
  sku: props.supply?.sku ?? null,
  category: props.supply?.category ?? "material",
  base_unit: props.supply?.base_unit ?? "unit",
  brand: props.supply?.brand ?? null,
  description: props.supply?.description ?? null,
  notes: props.supply?.notes ?? null,
  active: props.supply?.active ?? true,
});
const original = structuredClone(toRaw(body.value));
const confirmed = ref(false),
  state = useRecordedWrite(
    `supply:${props.supply?.id ?? "new"}`,
    props.refresh,
  );
const markSaved = useDraftGuard("supply-editor", () => body.value);
async function save() {
  if (!confirmed.value) return;
  const payload = {
    ...body.value,
    sku: body.value.sku || null,
    brand: body.value.brand || null,
    description: body.value.description || null,
    notes: body.value.notes || null,
  };
  const result = await state.run(
    `${body.value.name} · ${body.value.base_unit}`,
    () =>
      props.supply
        ? api.updateSupply(
            props.supply.id,
            Object.fromEntries(
              Object.entries(payload).filter(
                ([key, value]) =>
                  value !== original[key as keyof typeof original],
              ),
            ),
          )
        : api.createSupply(payload),
  );
  if (result) {
    Object.assign(original, payload);
    markSaved();
    confirmed.value = false;
    emit("saved", result.id);
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>{{ supply ? i.editSupply : i.newSupply }}</h2>
    <p>{{ i.unitHelp }}</p>
    <WriteStatus :state="state" />
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <label
          >{{ i.name
          }}<input v-model="body.name" required maxlength="255" /></label
        ><label>{{ i.sku }}<input v-model="body.sku" maxlength="100" /></label
        ><label
          >{{ i.category
          }}<select v-model="body.category">
            <option
              v-for="(label, value) in supplyCategories"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        ><label
          >{{ i.unit
          }}<select v-model="body.base_unit">
            <option
              v-for="(label, value) in supplyUnits"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        >
        <label
          >{{ i.brand }}<input v-model="body.brand" maxlength="255" /></label
        ><label
          >{{ i.description }}<textarea v-model="body.description" /></label
        ><label>{{ i.notes }}<textarea v-model="body.notes" /></label
        ><label class="catalog-check"
          ><input v-model="body.active" type="checkbox" />{{ i.active }}</label
        ><label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />{{
            i.confirm
          }}</label
        ><UButton type="submit">{{ i.save }}</UButton>
      </fieldset>
    </form>
  </section>
</template>
