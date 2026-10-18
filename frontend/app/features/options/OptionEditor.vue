<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { optionsApi, type OptionRecord, type Schema } from "./api";
import { productApi } from "~/features/products/api";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
const props = defineProps<{
  definition?: string;
  record?: OptionRecord;
  refresh: () => Promise<boolean>;
}>();
const emit = defineEmits<{ saved: [id: string] }>();
const base = useRuntimeConfig().public.apiBaseUrl,
  api = optionsApi(base),
  catalog = productApi(base);
const refs = useQuery({
  queryKey: ["option-references"],
  enabled: !!props.definition,
  retry: false,
  queryFn: async () => {
    const [families, supplies] = await Promise.all([
      catalog.families(),
      catalog.supplies(),
    ]);
    return { families, supplies };
  },
});
const body = ref<Schema["OptionValueCreate"]>({
  name: props.record?.name ?? "",
  description: props.record?.description ?? null,
  active: props.record?.active ?? true,
  ...(props.definition
    ? {
        family_id:
          props.record && "family_id" in props.record
            ? props.record.family_id
            : null,
        supply_id:
          props.record && "supply_id" in props.record
            ? props.record.supply_id
            : null,
      }
    : {}),
});
const original = structuredClone(toRaw(body.value)),
  confirmed = ref(false);
const state = useRecordedWrite(
  `option:${props.definition ?? "definitions"}:${props.record?.id ?? "new"}`,
  props.refresh,
);
const markSaved = useDraftGuard("option", () => body.value);
async function save() {
  if (!confirmed.value) return;
  const payload = {
    ...body.value,
    description: body.value.description || null,
  };
  const changes = Object.fromEntries(
    Object.entries(payload).filter(
      ([key, value]) => value !== original[key as keyof typeof original],
    ),
  );
  const result = await state.run(payload.name, () =>
    props.definition
      ? props.record
        ? api.updateOptionValue(props.definition, props.record.id, changes)
        : api.createOptionValue(props.definition, payload)
      : props.record
        ? api.updateOptionDefinition(props.record.id, changes)
        : api.createOptionDefinition(payload),
  );
  if (result) {
    Object.assign(original, payload);
    confirmed.value = false;
    markSaved();
    emit("saved", result.id);
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>{{ definition ? "Editar valor" : "Editar característica" }}</h2>
    <p>
      Catálogo compartido. Desactivar conserva identidad e historia, sin cambiar
      automáticamente el estado de los valores ni los productos que lo
      referencian. La API valida su uso posterior.
    </p>
    <WriteStatus :state="state" />
    <p v-if="refs.error.value" role="alert">
      {{ errorMessage(refs.error.value) }}
    </p>
    <UButton
      v-if="definition"
      color="neutral"
      variant="soft"
      @click="refs.refetch()"
      >Actualizar familias e insumos</UButton
    >
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <label
          >Nombre<input v-model="body.name" required maxlength="255"
        /></label>
        <label
          >Descripción<textarea v-model="body.description" maxlength="10000" />
        </label>
        <template v-if="definition">
          <p>
            Los vínculos son opcionales. «Sin vínculo» elimina sólo esa
            referencia al guardar. No cambia la familia o el insumo ni consume
            stock.
          </p>
          <label
            >Familia de diseño<select v-model="body.family_id">
              <option :value="null">Sin vínculo</option>
              <option
                v-if="
                  body.family_id &&
                  !refs.data.value?.families.some(
                    (row) => row.id === body.family_id,
                  )
                "
                :value="body.family_id"
              >
                Referencia actual · {{ body.family_id }}
              </option>
              <option
                v-for="row in refs.data.value?.families"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }}
              </option>
            </select></label
          >
          <label
            >Insumo<select v-model="body.supply_id">
              <option :value="null">Sin vínculo</option>
              <option
                v-if="
                  body.supply_id &&
                  !refs.data.value?.supplies.some(
                    (row) => row.id === body.supply_id,
                  )
                "
                :value="body.supply_id"
              >
                Referencia actual · {{ body.supply_id }}
              </option>
              <option
                v-for="row in refs.data.value?.supplies"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }} · {{ row.base_unit
                }}{{ row.active ? "" : " · Inactivo" }}
              </option>
            </select></label
          >
        </template>
        <label class="catalog-check"
          ><input v-model="body.active" type="checkbox" />Activo</label
        >
        <label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />Confirmo los
          datos y el estado del catálogo.</label
        >
        <UButton type="submit">Guardar cambios</UButton>
      </fieldset>
    </form>
  </section>
</template>
