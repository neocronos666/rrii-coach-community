<script setup lang="ts">
import type { ProductApi, Configuration, Schema, Selection } from "../api";
import type { Catalog } from "../useCatalog";
import { useEditor } from "../useEditor";
import { productMessages as p } from "~/i18n/products";
const props = defineProps<{
  api: ProductApi;
  productId: string;
  catalog: Catalog;
  configuration: Configuration;
  variants: Schema["VariantRead"][];
  version: number;
}>();
const variant = ref(""),
  quantity = ref("1"),
  selections = ref<Selection[]>([]),
  result = ref<Schema["ResolvedRecipe"]>();
const { busy, failure, act } = useEditor();
watch(
  () => props.version,
  () => {
    result.value = undefined;
    selections.value = [];
  },
);
watch([variant, quantity, selections], () => (result.value = undefined), {
  deep: true,
});
function toggle(definition_id: string, explicit: boolean) {
  selections.value = selections.value.filter(
    (row) => row.definition_id !== definition_id,
  );
  if (explicit) selections.value.push({ definition_id, values: [] });
}
function resolve() {
  return act(async () => {
    result.value = undefined;
    result.value = await props.api.resolve(props.productId, {
      variant_id: variant.value,
      quantity: quantity.value,
      selections: selections.value,
    });
  });
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>{{ p.preview }}</h2>
    <p>{{ p.previewHelp }}</p>
    <form class="asset-form" @submit.prevent="resolve">
      <fieldset :disabled="busy">
        <label
          >{{ p.variant
          }}<select v-model="variant" required>
            <option value="">{{ p.choose }}</option>
            <option v-for="row in variants" :key="row.id" :value="row.id">
              {{ row.name }}{{ row.active ? "" : ` (${p.inactiveLabel})` }}
            </option>
          </select></label
        ><label
          >{{ p.quantity
          }}<input v-model="quantity" inputmode="decimal" required
        /></label>
        <section
          v-for="option in configuration.options"
          :key="option.definition_id"
          class="catalog-group asset-form"
        >
          <h3>
            {{
              catalog.definitions.find((row) => row.id === option.definition_id)
                ?.name || option.definition_id
            }}
          </h3>
          <label
            >{{ p.selectionMode
            }}<select
              :value="
                selections.some(
                  (row) => row.definition_id === option.definition_id,
                )
                  ? 'explicit'
                  : 'defaults'
              "
              @change="
                toggle(
                  option.definition_id,
                  ($event.target as HTMLSelectElement).value === 'explicit',
                )
              "
            >
              <option value="defaults">{{ p.defaults }}</option>
              <option value="explicit">{{ p.explicit }}</option>
            </select></label
          >
          <template
            v-for="selection in selections.filter(
              (row) => row.definition_id === option.definition_id,
            )"
            :key="selection.definition_id"
            ><div
              v-for="(value, index) in selection.values"
              :key="index"
              class="catalog-row"
            >
              <label
                >{{ p.value
                }}<select v-model="value.value_id" required>
                  <option value="">{{ p.choose }}</option>
                  <option
                    v-for="allowed in option.values"
                    :key="allowed.value_id"
                    :value="allowed.value_id"
                  >
                    {{
                      catalog.values.find((row) => row.id === allowed.value_id)
                        ?.name || allowed.value_id
                    }}
                  </option>
                </select></label
              ><label
                >{{ p.selectionQuantity
                }}<input
                  v-model="value.quantity"
                  inputmode="decimal"
                  required /></label
              ><UButton
                color="neutral"
                variant="soft"
                @click="selection.values.splice(index, 1)"
                >{{ p.remove }}</UButton
              >
            </div>
            <UButton
              color="neutral"
              variant="soft"
              @click="selection.values.push({ value_id: '', quantity: '1' })"
              >{{ p.addSelection }}</UButton
            ></template
          >
        </section>
        <UButton type="submit" :loading="busy">{{ p.resolve }}</UButton>
      </fieldset>
    </form>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <section v-if="result" class="asset-form" :aria-label="p.resolved">
      <h3>{{ p.resolved }}</h3>
      <p>
        {{ p.omitted }}:
        {{ result.omitted_step_keys.join(", ") || p.noOmitted }}
      </p>
      <article
        v-for="step in result.plan.steps"
        :key="step.key"
        class="catalog-group"
      >
        <h4>{{ step.title }}</h4>
        <p>{{ p.dependencies }}: {{ step.depends_on?.join(", ") || p.none }}</p>
        <dl
          v-for="planned in result.planned_steps.filter(
            (row) => row.key === step.key,
          )"
          :key="planned.key"
        >
          <dt>{{ p.demand }}</dt>
          <dd>{{ planned.required_quantity }} {{ planned.unit }}</dd>
          <dt>{{ p.batches }}</dt>
          <dd>{{ planned.batches }}</dd>
          <dt>{{ p.capacity }}</dt>
          <dd>{{ planned.planned_capacity }}</dd>
        </dl>
        <p v-if="step.service_action">
          {{ p.serviceAction }}: {{ step.service_action }}
        </p>
        <ul>
          <li v-for="resource in step.resources" :key="resource.key">
            <template v-if="'asset_id' in resource"
              ><NuxtLink :to="`/assets/${resource.asset_id}`">{{
                resource.name
              }}</NuxtLink>
              · {{ p.revision }} {{ resource.revision_number }} ·
              {{ resource.quantity_per_batch }}</template
            >
          </li>
          <li v-for="supply in step.supply_inputs" :key="supply.supply_id">
            {{
              catalog.supplies.find((row) => row.id === supply.supply_id)
                ?.name || supply.supply_id
            }}
            · {{ supply.quantity_per_batch }}
          </li>
        </ul>
      </article>
    </section>
  </section>
</template>
