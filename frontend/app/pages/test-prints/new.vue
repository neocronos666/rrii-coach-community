<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "~/features/products/api";
import { useCatalog } from "~/features/products/useCatalog";
import { testPrintApi, type Schema } from "~/features/test-prints/api";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.fullPath });
const variantId = String(useRoute().query.variant || ""),
  base = useRuntimeConfig().public.apiBaseUrl,
  products = productApi(base),
  api = testPrintApi(base);
const variant = useQuery({
  queryKey: ["test-variant", variantId],
  queryFn: () => products.variant(variantId),
  enabled: !!variantId,
  retry: false,
});
const context = useQuery({
  queryKey: computed(() => [
    "test-create-context",
    variantId,
    variant.data.value?.product_id,
  ]),
  enabled: computed(() => !!variant.data.value),
  retry: false,
  queryFn: async () => {
    const product = variant.data.value!.product_id;
    const [baseRecipe, legacy, configuration] = await Promise.all([
      products.baseRecipe(product),
      api.recipes(variantId),
      products.configuration(product),
    ]);
    return {
      recipes: [...(baseRecipe ? [baseRecipe] : []), ...legacy],
      configuration,
    };
  },
});
const catalog = useCatalog(products),
  recipe = ref(""),
  quantity = ref("1"),
  selections = ref<NonNullable<Schema["TestPrintCreate"]["selections"]>>([]);
const registry = provideDraftGuard(t.unsaved);
const markSaved = useDraftGuard(
  "test-create",
  () => [recipe.value, quantity.value, selections.value],
  registry,
);
const mutation = usePending<Schema["TestPrintCreate"], Schema["TestPrintRead"]>(
  "create",
  api.create,
  "test-print",
);
const preview = ref<Schema["ProductionPreview"] | null>(null);
const previewBusy = ref(false),
  previewError = ref("");
let previewGeneration = 0;
watch(
  [recipe, quantity, selections],
  () => {
    previewGeneration++;
    preview.value = null;
    previewError.value = "";
  },
  { deep: true, flush: "sync" },
);
async function showPreview() {
  const generation = ++previewGeneration;
  previewBusy.value = true;
  preview.value = null;
  previewError.value = "";
  try {
    const result = await api.preview(recipe.value, {
      variant_id: variantId,
      target_quantity: quantity.value,
      selections: selections.value,
    });
    if (generation === previewGeneration) preview.value = result;
  } catch (error) {
    if (generation === previewGeneration)
      previewError.value = errorMessage(error);
  } finally {
    previewBusy.value = false;
  }
}
function mode(id: string, explicit: boolean) {
  selections.value = selections.value.filter((row) => row.definition_id !== id);
  if (explicit) selections.value.push({ definition_id: id, values: [] });
}
async function create() {
  const result = await mutation.run({
    recipe_id: recipe.value,
    variant_id: variantId,
    target_quantity: quantity.value,
    selections: selections.value,
    machine_assignments: {},
  });
  if (result) {
    markSaved();
    await navigateTo(`/test-prints/${result.id}`);
  }
}
useHead({ title: `${t.new} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/products" color="neutral" variant="soft">{{
      t.products
    }}</UButton>
    <h1>{{ t.new }}</h1>
    <p>{{ t.creationHelp }}</p>
    <div
      v-if="variant.error.value || context.error.value || catalog.error.value"
      role="alert"
    >
      {{
        errorMessage(
          variant.error.value || context.error.value || catalog.error.value,
        )
      }}<UButton
        @click="
          variant.refetch();
          context.refetch();
          catalog.refetch();
        "
        >{{ t.retry }}</UButton
      >
    </div>
    <p v-if="variant.data.value">
      {{ t.variant }}: {{ variant.data.value.name }} ·
      {{ variant.data.value.base_unit }}
    </p>
    <PendingStatus
      :pending="!!mutation.pending.value"
      :busy="mutation.busy.value"
      :error="mutation.error.value"
      :persistent="mutation.persistent.value"
      :invalid="mutation.invalid.value"
      @retry="create"
      @clear="mutation.clearInvalid"
    />
    <form
      v-if="variant.data.value"
      class="asset-panel asset-form"
      @submit.prevent="create"
    >
      <fieldset
        :disabled="
          !mutation.ready.value ||
          mutation.busy.value ||
          !!mutation.pending.value ||
          mutation.invalid.value
        "
      >
        <label
          >{{ t.recipe
          }}<select v-model="recipe" required>
            <option value="">{{ t.choose }}</option>
            <option
              v-for="row in context.data.value?.recipes"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }}
            </option>
          </select></label
        >
        <label
          >{{ t.quantity
          }}<input v-model="quantity" inputmode="decimal" required
        /></label>
        <h2>{{ t.options }}</h2>
        <section
          v-for="option in context.data.value?.configuration.options"
          :key="option.definition_id"
          class="catalog-group asset-form"
        >
          <h3>
            {{
              catalog.data.value?.definitions.find(
                (row) => row.id === option.definition_id,
              )?.name || option.definition_id
            }}
          </h3>
          <label
            >{{ t.mode
            }}<select
              :value="
                selections.some(
                  (row) => row.definition_id === option.definition_id,
                )
                  ? 'explicit'
                  : 'defaults'
              "
              @change="
                mode(
                  option.definition_id,
                  ($event.target as HTMLSelectElement).value === 'explicit',
                )
              "
            >
              <option value="defaults">{{ t.defaults }}</option>
              <option value="explicit">{{ t.explicit }}</option>
            </select></label
          >
          <template
            v-for="selection in selections.filter(
              (row) => row.definition_id === option.definition_id,
            )"
            :key="selection.definition_id"
          >
            <div
              v-for="(value, index) in selection.values"
              :key="index"
              class="catalog-row"
            >
              <label
                >{{ t.value
                }}<select v-model="value.value_id" required>
                  <option value="">{{ t.choose }}</option>
                  <option
                    v-for="allowed in option.values"
                    :key="allowed.value_id"
                    :value="allowed.value_id"
                  >
                    {{
                      catalog.data.value?.values.find(
                        (row) => row.id === allowed.value_id,
                      )?.name || allowed.value_id
                    }}
                  </option>
                </select></label
              >
              <label
                >{{ t.selectedQuantity
                }}<input
                  v-model="value.quantity"
                  inputmode="decimal"
                  required /></label
              ><UButton
                color="neutral"
                variant="soft"
                @click="selection.values.splice(index, 1)"
                >{{ t.remove }}</UButton
              >
            </div>
            <UButton
              color="neutral"
              variant="soft"
              @click="selection.values.push({ value_id: '', quantity: '1' })"
              >{{ t.add }}</UButton
            >
          </template>
        </section>
        <UButton
          type="button"
          color="neutral"
          variant="soft"
          :disabled="!recipe || !quantity || previewBusy"
          @click="showPreview"
          >{{ t.preview }}</UButton
        >
        <p v-if="previewBusy" role="status">{{ t.loading }}</p>
        <p v-if="previewError" role="alert">{{ previewError }}</p>
        <section
          v-if="preview"
          class="asset-panel"
          aria-labelledby="preview-title"
          data-testid="recipe-preview"
        >
          <h2 id="preview-title">{{ t.preview }}</h2>
          <p>{{ t.previewHelp }}</p>
          <ul>
            <li v-for="step in preview.steps" :key="step.key">
              {{ step.key }} · {{ t.requiredQuantity }}:
              {{ step.required_quantity }} {{ step.unit }} · {{ t.batches }}:
              {{ step.batches }} · {{ t.capacity }}: {{ step.planned_capacity }}
              {{ step.unit }}
            </li>
          </ul>
          <p v-if="preview.omitted_step_keys?.length">
            {{ t.omitted }}: {{ preview.omitted_step_keys.join(", ") }}
          </p>
        </section>
        <UButton type="submit">{{ t.create }}</UButton>
      </fieldset>
    </form>
  </div>
</template>
