<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "~/features/products/api";
import { useCatalog } from "~/features/products/useCatalog";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import {
  quickQuoteApi,
  newDefinition,
  type Definition,
  type Schema,
} from "../api";
import { quickQuoteMessages as q, laborLabels } from "~/i18n/quick-quotes";
import PricingResult from "./PricingResult.vue";
const props = defineProps<{
  initial?: Definition;
  productId?: string;
  locked?: boolean;
  submitLabel: string;
}>();
const emit = defineEmits<{ save: [definition: Definition] }>();
const draft = ref<Definition>(
  props.initial ? JSON.parse(JSON.stringify(props.initial)) : newDefinition(),
);
const product = ref(props.productId ?? ""),
  estimateKey = ref(""),
  busy = ref(false),
  failure = ref(""),
  preview = ref<Schema["PricingPreviewRead"]>();
const api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl),
  products = productApi(useRuntimeConfig().public.apiBaseUrl),
  catalog = useCatalog(products);
const variants = useQuery({
  queryKey: computed(() => ["product-variants", product.value]),
  queryFn: () => products.variants(product.value),
  enabled: computed(() => !!product.value),
  retry: false,
});
const recipes = useQuery({
  queryKey: computed(() => [
    "quote-recipes",
    product.value,
    draft.value.pricing.variant_id,
  ]),
  queryFn: async () => {
    const [base, legacy] = await Promise.all([
      products.baseRecipe(product.value),
      api.recipes(draft.value.pricing.variant_id),
    ]);
    return [...(base ? [base] : []), ...legacy];
  },
  enabled: computed(() => !!product.value && !!draft.value.pricing.variant_id),
  retry: false,
});
const plan = useQuery({
  queryKey: computed(() => ["recipe-plan", draft.value.pricing.recipe_id]),
  queryFn: () => products.plan(draft.value.pricing.recipe_id),
  enabled: computed(() => !!draft.value.pricing.recipe_id),
  retry: false,
});
const configuration = useQuery({
  queryKey: computed(() => ["product-configuration", product.value]),
  queryFn: () => products.configuration(product.value),
  enabled: computed(() => !!product.value),
  retry: false,
});
const machines = useQuery({
  queryKey: ["quote-machines"],
  queryFn: () => api.machines(),
  retry: false,
});
const markSaved = useDraftGuard("quick-quote-definition", () => [
  product.value,
  draft.value,
]);
defineExpose({ markSaved });
watch(draft, () => (preview.value = undefined), { deep: true });
function identityChanged(changeProduct: boolean) {
  const variant = changeProduct ? "" : draft.value.pricing.variant_id;
  draft.value.pricing = {
    ...newDefinition().pricing,
    variant_id: variant,
    target_quantity: draft.value.pricing.target_quantity,
    markup_percentage: draft.value.pricing.markup_percentage,
    strategy: draft.value.pricing.strategy,
  };
}
function mode(definition_id: string, explicit: boolean) {
  draft.value.pricing.selections = (
    draft.value.pricing.selections ?? []
  ).filter((row) => row.definition_id !== definition_id);
  if (explicit)
    draft.value.pricing.selections.push({ definition_id, values: [] });
}
function addEstimate() {
  draft.value.pricing.step_estimates ??= {};
  draft.value.pricing.step_estimates[estimateKey.value] = {
    labor: [],
    extras: [],
    machine_id: null,
    machine_duration_minutes: null,
    energy_kwh: null,
  };
  estimateKey.value = "";
}
async function evaluate() {
  busy.value = true;
  failure.value = "";
  preview.value = undefined;
  try {
    preview.value = await api.preview(draft.value.pricing);
  } catch (error) {
    failure.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}
const loadError = computed(
  () =>
    catalog.error.value ||
    variants.error.value ||
    recipes.error.value ||
    plan.error.value ||
    configuration.error.value ||
    machines.error.value,
);
async function reload() {
  await Promise.all([
    catalog.refetch(),
    machines.refetch(),
    ...(product.value ? [variants.refetch(), configuration.refetch()] : []),
    ...(draft.value.pricing.variant_id ? [recipes.refetch()] : []),
    ...(draft.value.pricing.recipe_id ? [plan.refetch()] : []),
  ]);
}
</script>
<template>
  <div class="asset-form">
    <div v-if="loadError" role="alert">
      <p>{{ q.catalogError }}</p>
      <p>{{ errorMessage(loadError) }}</p>
      <UButton @click="reload">{{ q.retry }}</UButton>
    </div>
    <form class="asset-panel asset-form" @submit.prevent="emit('save', draft)">
      <fieldset :disabled="locked || busy">
        <label
          >{{ q.name
          }}<input v-model="draft.title" required maxlength="255" /></label
        ><label
          >{{ q.notes }}<textarea v-model="draft.notes" maxlength="10000" />
        </label>
        <p>{{ q.identityHelp }}</p>
        <label
          >{{ q.product
          }}<select v-model="product" required @change="identityChanged(true)">
            <option value="">{{ q.choose }}</option>
            <option
              v-if="
                product &&
                !catalog.data.value?.products.some((row) => row.id === product)
              "
              :value="product"
            >
              {{ product }}
            </option>
            <option
              v-for="row in catalog.data.value?.products"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }}
            </option>
          </select></label
        ><label
          >{{ q.variant
          }}<select
            v-model="draft.pricing.variant_id"
            required
            @change="identityChanged(false)"
          >
            <option value="">{{ q.choose }}</option>
            <option
              v-if="
                draft.pricing.variant_id &&
                !variants.data.value?.some(
                  (row) => row.id === draft.pricing.variant_id,
                )
              "
              :value="draft.pricing.variant_id"
            >
              {{ draft.pricing.variant_id }}
            </option>
            <option
              v-for="row in variants.data.value"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }}
            </option>
          </select></label
        ><label
          >{{ q.recipe
          }}<select v-model="draft.pricing.recipe_id" required>
            <option value="">{{ q.choose }}</option>
            <option
              v-if="
                draft.pricing.recipe_id &&
                !recipes.data.value?.some(
                  (row) => row.id === draft.pricing.recipe_id,
                )
              "
              :value="draft.pricing.recipe_id"
            >
              {{ draft.pricing.recipe_id }}
            </option>
            <option
              v-for="row in recipes.data.value"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }}
            </option>
          </select></label
        >
        <div class="catalog-row">
          <label
            >{{ q.quantity
            }}<input
              v-model="draft.pricing.target_quantity"
              inputmode="decimal"
              required /></label
          ><label
            >{{ q.strategy
            }}<select v-model="draft.pricing.strategy">
              <option value="fifo">{{ q.fifo }}</option>
              <option value="last_purchase">{{ q.lastPurchase }}</option>
            </select></label
          >
        </div>
        <label
          >{{ q.markup
          }}<input
            :value="draft.pricing.markup_percentage ?? ''"
            inputmode="decimal"
            @input="
              draft.pricing.markup_percentage =
                ($event.target as HTMLInputElement).value || null
            "
        /></label>
        <p>{{ q.markupHelp }}</p>
        <h3>{{ q.options }}</h3>
        <section
          v-for="option in configuration.data.value?.options ?? []"
          :key="option.definition_id"
          class="catalog-group asset-form"
        >
          <h4>
            {{
              catalog.data.value?.definitions.find(
                (row) => row.id === option.definition_id,
              )?.name || option.definition_id
            }}
          </h4>
          <label
            >{{ q.mode
            }}<select
              :value="
                draft.pricing.selections?.some(
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
              <option value="defaults">{{ q.defaults }}</option>
              <option value="explicit">{{ q.explicit }}</option>
            </select></label
          ><template
            v-for="selection in draft.pricing.selections?.filter(
              (row) => row.definition_id === option.definition_id,
            )"
            :key="selection.definition_id"
            ><div
              v-for="(value, index) in selection.values"
              :key="index"
              class="catalog-row"
            >
              <label
                >{{ q.value
                }}<select v-model="value.value_id" required>
                  <option value="">{{ q.choose }}</option>
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
              ><label
                >{{ q.selectedQuantity
                }}<input
                  v-model="value.quantity"
                  inputmode="decimal"
                  required /></label
              ><UButton
                color="neutral"
                variant="soft"
                @click="selection.values.splice(index, 1)"
                >{{ q.remove }}</UButton
              >
            </div>
            <UButton
              color="neutral"
              variant="soft"
              @click="selection.values.push({ value_id: '', quantity: '1' })"
              >{{ q.addSelection }}</UButton
            ></template
          >
        </section>
        <div
          v-for="selection in draft.pricing.selections?.filter(
            (row) =>
              !configuration.data.value?.options.some(
                (option) => option.definition_id === row.definition_id,
              ),
          )"
          :key="selection.definition_id"
          class="catalog-group"
        >
          <p>{{ q.options }}: {{ selection.definition_id }}</p>
          <UButton
            color="neutral"
            variant="soft"
            @click="mode(selection.definition_id, false)"
            >{{ q.remove }}</UButton
          >
        </div>
        <h3>{{ q.estimates }}</h3>
        <p>{{ q.estimateHelp }}</p>
        <section
          v-for="(estimate, key) in draft.pricing.step_estimates"
          :key="key"
          class="catalog-group asset-form"
          :aria-label="`${q.step} ${key}`"
        >
          <h4>
            {{
              plan.data.value?.steps.find((row) => row.key === key)?.title ||
              key
            }}
          </h4>
          <label
            >{{ q.machine
            }}<select v-model="estimate.machine_id">
              <option :value="null">{{ q.none }}</option>
              <option
                v-for="row in machines.data.value"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }}
              </option>
            </select></label
          ><label
            >{{ q.minutes
            }}<input
              :value="estimate.machine_duration_minutes ?? ''"
              type="number"
              min="1"
              step="1"
              @input="
                estimate.machine_duration_minutes =
                  ($event.target as HTMLInputElement).value === ''
                    ? null
                    : Number(($event.target as HTMLInputElement).value)
              " /></label
          ><label
            >{{ q.energy
            }}<input
              :value="estimate.energy_kwh ?? ''"
              inputmode="decimal"
              @input="
                estimate.energy_kwh =
                  ($event.target as HTMLInputElement).value || null
              "
          /></label>
          <h4>{{ q.labor }}</h4>
          <div
            v-for="(labor, index) in estimate.labor"
            :key="index"
            class="catalog-row"
          >
            <label
              >{{ q.laborType
              }}<select v-model="labor.labor_type">
                <option
                  v-for="(label, value) in laborLabels"
                  :key="value"
                  :value="value"
                >
                  {{ label }}
                </option>
              </select></label
            ><label
              >{{ q.laborMinutes
              }}<input
                v-model.number="labor.duration_minutes"
                type="number"
                min="1"
                step="1"
                required /></label
            ><UButton
              color="neutral"
              variant="soft"
              @click="estimate.labor?.splice(index, 1)"
              >{{ q.remove }}</UButton
            >
          </div>
          <UButton
            color="neutral"
            variant="soft"
            @click="
              (estimate.labor ??= []).push({
                labor_type: 'assembly',
                duration_minutes: 1,
              })
            "
            >{{ q.addLabor }}</UButton
          >
          <h4>{{ q.extras }}</h4>
          <div
            v-for="(extra, index) in estimate.extras"
            :key="index"
            class="catalog-group asset-form"
          >
            <label
              >{{ q.extraDescription
              }}<input
                v-model="extra.description"
                required
                maxlength="1000" /></label
            ><label
              >{{ q.amount
              }}<input
                v-model="extra.amount"
                inputmode="decimal"
                required /></label
            ><label
              >{{ q.currency
              }}<input
                v-model="extra.currency"
                required
                minlength="3"
                maxlength="3" /></label
            ><UButton
              color="neutral"
              variant="soft"
              @click="estimate.extras?.splice(index, 1)"
              >{{ q.remove }}</UButton
            >
          </div>
          <UButton
            color="neutral"
            variant="soft"
            @click="
              (estimate.extras ??= []).push({
                description: '',
                amount: '0',
                currency: 'ARS',
              })
            "
            >{{ q.addExtra }}</UButton
          ><UButton
            color="neutral"
            variant="soft"
            @click="delete draft.pricing.step_estimates![key]"
            >{{ q.removeEstimate }}</UButton
          >
        </section>
        <label
          >{{ q.step
          }}<select v-model="estimateKey">
            <option value="">{{ q.choose }}</option>
            <option
              v-for="step in plan.data.value?.steps.filter(
                (row) => !draft.pricing.step_estimates?.[row.key],
              ) ?? []"
              :key="step.key"
              :value="step.key"
            >
              {{ step.title }} · {{ step.key }}
            </option>
          </select></label
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="!estimateKey"
          @click="addEstimate"
          >{{ q.addEstimate }}</UButton
        >
        <p>{{ q.saveHelp }}</p>
        <div class="asset-actions">
          <UButton
            color="neutral"
            variant="soft"
            :disabled="locked || busy"
            @click="evaluate"
            >{{ q.preview }}</UButton
          ><UButton type="submit" :disabled="locked || busy">{{
            submitLabel
          }}</UButton>
        </div>
      </fieldset>
    </form>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <PricingResult
      v-if="preview"
      :preview="preview"
      :heading="q.previewTitle"
    />
  </div>
</template>
