<script setup lang="ts">
import { detailsApi, type Schema } from "./api";
import { assetDraft, assetChanges, textFields } from "./fields";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{
  asset: Schema["AssetRead"];
  categories: Schema["CategoryRead"][];
  families: Schema["FamilyRead"][];
  refresh: () => Promise<boolean>;
}>();
const api = detailsApi(useRuntimeConfig().public.apiBaseUrl),
  body = ref(assetDraft(props.asset));
let original = assetDraft(props.asset);
const confirmed = ref(false),
  markSaved = useDraftGuard("asset-metadata", () => body.value);
const state = useRecordedWrite(
  `asset-metadata:${props.asset.id}`,
  props.refresh,
);
async function save() {
  if (!confirmed.value) return;
  const row = await state.run(body.value.name, () =>
    api.update(props.asset.id, assetChanges(body.value, original)),
  );
  if (row) {
    body.value = assetDraft(row);
    original = assetDraft(row);
    confirmed.value = false;
    markSaved();
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Editar datos del Asset</h2>
    <p>
      Estos datos son actuales y compartidos por sus revisiones. Guardar no crea
      revisiones, no cambia archivos ni modifica referencias históricas. Las
      condiciones de uso son información descriptiva.
    </p>
    <WriteStatus :state="state" />
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <label v-for="field in textFields" :key="field.key"
          >{{ field.label
          }}<textarea
            v-if="field.max === 10000"
            v-model="body[field.key]"
            :maxlength="field.max" /><input
            v-else
            v-model="body[field.key]"
            :required="field.required"
            :maxlength="field.max"
        /></label>
        <label
          >Categoría<select v-model="body.category_id" required>
            <option
              v-if="!categories.some((row) => row.id === body.category_id)"
              :value="body.category_id"
            >
              Referencia actual · {{ body.category_id }}
            </option>
            <option v-for="row in categories" :key="row.id" :value="row.id">
              {{ row.name }}{{ row.system_key ? " · Sistema" : "" }}
            </option>
          </select></label
        ><NuxtLink to="/asset-categories">Administrar categorías</NuxtLink>
        <label
          >Familia de diseño<select v-model="body.family_id">
            <option :value="null">Sin familia</option>
            <option
              v-if="
                body.family_id &&
                !families.some((row) => row.id === body.family_id)
              "
              :value="body.family_id"
            >
              Referencia actual · {{ body.family_id }}
            </option>
            <option v-for="row in families" :key="row.id" :value="row.id">
              {{ row.name }}
            </option>
          </select></label
        >
        <label class="catalog-check"
          ><input v-model="body.third_party" type="checkbox" />Recurso de
          terceros</label
        ><label class="catalog-check"
          ><input v-model="body.archived" type="checkbox" />Archivado</label
        ><label class="catalog-check"
          ><input v-model="confirmed" required type="checkbox" />Confirmo los
          datos y el estado del Asset.</label
        ><UButton type="submit">Guardar datos del Asset</UButton>
      </fieldset>
    </form>
  </section>
</template>
