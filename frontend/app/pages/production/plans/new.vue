<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "~/features/products/api";
import { useCatalog } from "~/features/products/useCatalog";
import { testPrintApi } from "~/features/test-prints/api";
import { commercialApi } from "~/features/commercial/api";
import {
  productionApi,
  type Schema,
  type Destination,
} from "~/features/production/api";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { productionMessages as p } from "~/i18n/production";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.fullPath });
const route = useRoute(),
  base = useRuntimeConfig().public.apiBaseUrl;
const orderId = typeof route.query.order === "string" ? route.query.order : "";
const projectId =
  typeof route.query.project === "string" ? route.query.project : "";
const componentId =
  typeof route.query.component === "string" ? route.query.component : "";
const destination: Destination | null =
  orderId && !projectId && !componentId
    ? { kind: "order", id: orderId }
    : !orderId && projectId && componentId
      ? { kind: "component", id: componentId }
      : null;
const products = productApi(base),
  helper = testPrintApi(base),
  api = productionApi(base),
  commercial = commercialApi(base);
const origin = useQuery({
  queryKey: ["production-origin", orderId, projectId, componentId],
  enabled: !!destination,
  retry: false,
  queryFn: async () => {
    if (orderId) {
      const row = await commercial.order(orderId);
      return {
        title: `${row.code} · ${row.title}`,
        quantity: row.quantity,
        status: row.status,
        url: `/orders/${row.id}`,
        quote: row.source_quote_id,
      };
    }
    const project = await commercial.project(projectId);
    const row = project.components.find((item) => item.id === componentId);
    if (!row) throw new Error(p.originRequired);
    return {
      title: `${project.code} · ${row.description}`,
      quantity: row.quantity,
      status: project.status,
      url: `/projects/${project.id}`,
      quote: project.source_quote_id,
    };
  },
});
const catalog = useCatalog(products),
  productId = ref(""),
  variantId = ref(""),
  recipe = ref(""),
  quantity = ref("");
const selections = ref<
  NonNullable<Schema["ProductionPlanCreate"]["selections"]>
>([]);
const reserve = ref(true),
  allocate = ref(true),
  confirmed = ref(false),
  assignments = ref<Record<string, string>>({});
const variants = useQuery({
  queryKey: computed(() => ["production-variants", productId.value]),
  enabled: computed(() => !!productId.value),
  queryFn: () => products.variants(productId.value),
  retry: false,
});
const context = useQuery({
  queryKey: computed(() => [
    "production-recipes",
    productId.value,
    variantId.value,
  ]),
  enabled: computed(() => !!productId.value && !!variantId.value),
  retry: false,
  queryFn: async () => {
    const [baseRecipe, legacy, configuration] = await Promise.all([
      products.baseRecipe(productId.value),
      helper.recipes(variantId.value),
      products.configuration(productId.value),
    ]);
    return {
      recipes: [...(baseRecipe ? [baseRecipe] : []), ...legacy],
      configuration,
    };
  },
});
const machines = useQuery({
  queryKey: ["quote-machines"],
  queryFn: helper.machines,
  retry: false,
});
watch(
  productId,
  () => {
    variantId.value = "";
    selections.value = [];
  },
  { flush: "sync" },
);
watch(
  variantId,
  () => {
    recipe.value = "";
  },
  { flush: "sync" },
);
const registry = provideDraftGuard(t.unsaved);
const markSaved = useDraftGuard(
  "production-create",
  () => [
    productId.value,
    variantId.value,
    recipe.value,
    quantity.value,
    selections.value,
    reserve.value,
    allocate.value,
    assignments.value,
  ],
  registry,
);
const mutation = usePending<
  Schema["ProductionPlanCreate"],
  Schema["ProductionPlanRead"]
>(
  `create:${destination?.kind}:${destination?.id}`,
  (body) => {
    if (!destination) throw new Error(p.originRequired);
    return api.create(destination, body);
  },
  "production",
);
const preview = ref<Schema["ProductionPreview"] | null>(null),
  previewBusy = ref(false),
  previewError = ref("");
let generation = 0;
watch(
  [recipe, variantId, quantity, selections],
  () => {
    generation++;
    preview.value = null;
    previewError.value = "";
    assignments.value = {};
    confirmed.value = false;
  },
  { deep: true, flush: "sync" },
);
watch(
  [reserve, allocate, assignments],
  () => {
    confirmed.value = false;
  },
  { deep: true },
);
async function showPreview() {
  const current = ++generation;
  previewBusy.value = true;
  preview.value = null;
  previewError.value = "";
  confirmed.value = false;
  try {
    const result = await helper.preview(recipe.value, {
      variant_id: variantId.value,
      target_quantity: quantity.value,
      selections: selections.value,
    });
    if (current === generation) preview.value = result;
  } catch (error) {
    if (current === generation) previewError.value = errorMessage(error);
  } finally {
    previewBusy.value = false;
  }
}
function mode(id: string, explicit: boolean) {
  selections.value = selections.value.filter((row) => row.definition_id !== id);
  if (explicit) selections.value.push({ definition_id: id, values: [] });
}
async function create() {
  if (
    !mutation.pending.value &&
    (!confirmed.value ||
      !preview.value ||
      origin.data.value?.status !== "pending")
  )
    return;
  const result = await mutation.run({
    recipe_id: recipe.value,
    variant_id: variantId.value,
    target_quantity: quantity.value,
    selections: selections.value,
    reserve_supplies: reserve.value,
    allocate_output: allocate.value,
    machine_assignments: Object.fromEntries(
      Object.entries(assignments.value).filter(([, value]) => value),
    ),
  });
  if (result) {
    markSaved();
    await navigateTo(`/production/plans/${result.id}`);
  }
}
useHead({ title: `${p.new} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/production" color="neutral" variant="soft">{{
      p.title
    }}</UButton>
    <h1>{{ p.new }}</h1>
    <p>{{ p.creationHelp }}</p>
    <p v-if="!destination" role="alert">{{ p.originRequired }}</p>
    <p v-if="destination && origin.isPending.value" role="status">
      {{ t.loading }}
    </p>
    <section v-if="origin.data.value" class="asset-panel asset-form">
      <h2>{{ origin.data.value.title }}</h2>
      <p>{{ p.sourceQuantity }}: {{ origin.data.value.quantity }}</p>
      <div class="asset-actions">
        <UButton :to="origin.data.value.url" color="neutral" variant="soft">{{
          p.source
        }}</UButton
        ><UButton
          :to="`/quotes/${origin.data.value.quote}`"
          color="neutral"
          variant="soft"
          >{{ p.sourceQuote }}</UButton
        >
      </div>
      <p v-if="origin.data.value.status !== 'pending'" role="alert">
        {{ p.cancelledOrigin }}
      </p>
    </section>
    <div
      v-if="
        origin.error.value ||
        catalog.error.value ||
        variants.error.value ||
        context.error.value
      "
      role="alert"
    >
      {{
        errorMessage(
          origin.error.value ||
            catalog.error.value ||
            variants.error.value ||
            context.error.value,
        )
      }}<UButton
        @click="
          origin.refetch();
          catalog.refetch();
          variants.refetch();
          context.refetch();
        "
        >{{ t.retry }}</UButton
      >
    </div>
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
      v-if="origin.data.value?.status === 'pending'"
      class="asset-form"
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
          >Producto<select v-model="productId" required>
            <option value="">{{ t.choose }}</option>
            <option
              v-for="row in catalog.data.value?.products"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }}
            </option>
          </select></label
        >
        <label
          >{{ t.variant
          }}<select v-model="variantId" required>
            <option value="">{{ t.choose }}</option>
            <option
              v-for="row in variants.data.value"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }} · {{ row.base_unit }}
            </option>
          </select></label
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
          class="asset-panel asset-form"
          data-testid="production-preview"
        >
          <h2>{{ t.preview }}</h2>
          <p>{{ p.previewHelp }}</p>
          <ul>
            <li v-for="step in preview.steps" :key="step.key">
              {{ step.key }} · {{ t.requiredQuantity }}:
              {{ step.required_quantity }} {{ step.unit }} · {{ t.batches }}:
              {{ step.batches }} · {{ t.capacity }}: {{ step.planned_capacity }}
            </li>
          </ul>
          <p>
            {{ t.omitted }}:
            {{ preview.omitted_step_keys?.join(", ") || t.none }}
          </p>
          <div v-if="machines.error.value" role="alert">
            {{ errorMessage(machines.error.value)
            }}<UButton @click="machines.refetch()">{{ t.retry }}</UButton>
          </div>
          <p>{{ t.machineHelp }}</p>
          <label v-for="step in preview.steps" :key="step.key"
            >{{ p.machine }} · {{ step.key
            }}<select
              :value="assignments[step.key] || ''"
              @change="
                assignments[step.key] = (
                  $event.target as HTMLSelectElement
                ).value
              "
            >
              <option value="">{{ t.none }}</option>
              <option
                v-for="row in machines.data.value"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }}
              </option>
            </select></label
          >
        </section>
        <label class="catalog-check"
          ><input v-model="reserve" type="checkbox" />{{ p.reserve }}</label
        >
        <label class="catalog-check"
          ><input v-model="allocate" type="checkbox" />{{ p.allocate }}</label
        >
        <p>{{ p.effects }}</p>
        <label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />{{
            p.confirm
          }}</label
        >
        <UButton type="submit" :disabled="!preview || !confirmed">{{
          p.create
        }}</UButton>
      </fieldset>
    </form>
  </div>
</template>
