<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import type { ProductApi, Configuration } from "../api";
import type { Catalog } from "../useCatalog";
import { useDraftGuard } from "../useDraftGuard";
import { useEditor } from "../useEditor";
import { errorMessage } from "~/features/shared/http";
import { productMessages as p } from "~/i18n/products";
const props = defineProps<{
  api: ProductApi;
  productId: string;
  catalog: Catalog;
}>();
const emit = defineEmits<{ saved: [] }>();
const cache = useQueryClient(),
  draft = ref<Configuration>({ options: [] }),
  ready = ref(false),
  definition = ref("");
const { busy, failure, success, act } = useEditor();
const markSaved = useDraftGuard("configuration", () => draft.value);
const query = useQuery({
  queryKey: ["product-configuration", props.productId],
  queryFn: () => props.api.configuration(props.productId),
  retry: false,
});
watch(
  query.data,
  (data) => {
    if (data && !ready.value) {
      draft.value = { options: structuredClone(toRaw(data.options)) };
      ready.value = true;
      markSaved();
    }
  },
  { immediate: true },
);
const definitionName = ref(""),
  valueName = ref(""),
  valueDefinition = ref(""),
  family = ref(""),
  supply = ref("");
function add() {
  draft.value.options.push({
    definition_id: definition.value,
    min_selections: 0,
    max_selections: 1,
    context_asset_id: null,
    context_definition_id: null,
    values: [],
  });
  definition.value = "";
}
function save() {
  return act(async () => {
    const data = await props.api.saveConfiguration(
      props.productId,
      draft.value,
    );
    draft.value = { options: structuredClone(data.options) };
    cache.setQueryData(["product-configuration", props.productId], data);
    markSaved();
    emit("saved");
  });
}
function createDefinition() {
  return act(async () => {
    const row = await props.api.createDefinition({
      name: definitionName.value,
      active: true,
    });
    await cache.invalidateQueries({ queryKey: ["product-editor-catalog"] });
    valueDefinition.value = row.id;
    definition.value = row.id;
    definitionName.value = "";
  });
}
function createValue() {
  return act(async () => {
    await props.api.createValue(valueDefinition.value, {
      name: valueName.value,
      active: true,
      family_id: family.value || null,
      supply_id: supply.value || null,
    });
    await cache.invalidateQueries({ queryKey: ["product-editor-catalog"] });
    valueName.value = "";
  });
}
</script>
<template>
  <UButton to="/options" color="neutral" variant="soft"
    >Administrar opciones y valores</UButton
  >
  <section class="asset-panel asset-form">
    <h2>{{ p.options }}</h2>
    <p>{{ p.optionHelp }}</p>
    <p v-if="query.isPending.value" role="status">{{ p.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ p.retry }}</UButton>
    </div>
    <form v-if="ready" class="asset-form" @submit.prevent="save">
      <fieldset :disabled="busy">
        <section
          v-for="(option, index) in draft.options"
          :key="option.definition_id"
          class="catalog-group asset-form"
          :aria-label="
            catalog.definitions.find((row) => row.id === option.definition_id)
              ?.name || option.definition_id
          "
        >
          <h3>
            {{
              catalog.definitions.find((row) => row.id === option.definition_id)
                ?.name || option.definition_id
            }}
          </h3>
          <div class="catalog-row">
            <label
              >{{ p.min
              }}<input
                v-model.number="option.min_selections"
                type="number"
                min="0"
                step="1"
                required /></label
            ><label
              >{{ p.max
              }}<input
                :value="option.max_selections ?? ''"
                type="number"
                min="0"
                step="1"
                :placeholder="p.unlimited"
                @input="
                  option.max_selections =
                    ($event.target as HTMLInputElement).value === ''
                      ? null
                      : Number(($event.target as HTMLInputElement).value)
                "
            /></label>
          </div>
          <label
            >{{ p.contextAsset
            }}<select v-model="option.context_asset_id">
              <option :value="null">{{ p.none }}</option>
              <option
                v-for="asset in catalog.assets"
                :key="asset.id"
                :value="asset.id"
              >
                {{ asset.name }}
              </option>
            </select></label
          >
          <label
            >{{ p.contextDefinition
            }}<select v-model="option.context_definition_id">
              <option :value="null">{{ p.none }}</option>
              <option
                v-for="other in draft.options.filter(
                  (row) => row.definition_id !== option.definition_id,
                )"
                :key="other.definition_id"
                :value="other.definition_id"
              >
                {{
                  catalog.definitions.find(
                    (row) => row.id === other.definition_id,
                  )?.name || other.definition_id
                }}
              </option>
            </select></label
          >
          <p>{{ p.contextHelp }}</p>
          <h4>{{ p.allowed }}</h4>
          <div
            v-for="(value, valueIndex) in option.values"
            :key="valueIndex"
            class="catalog-row"
          >
            <label
              >{{ p.value
              }}<select v-model="value.value_id" required>
                <option value="">{{ p.choose }}</option>
                <option
                  v-for="entry in catalog.values.filter(
                    (row) => row.definition_id === option.definition_id,
                  )"
                  :key="entry.id"
                  :value="entry.id"
                >
                  {{ entry.name
                  }}{{ entry.active ? "" : ` (${p.inactiveLabel})` }}
                </option>
              </select></label
            ><label
              >{{ p.defaultQuantity
              }}<input
                :value="value.default_quantity ?? ''"
                inputmode="decimal"
                @input="
                  value.default_quantity =
                    ($event.target as HTMLInputElement).value || null
                " /></label
            ><UButton
              color="neutral"
              variant="soft"
              @click="option.values.splice(valueIndex, 1)"
              >{{ p.remove }} {{ p.value }}</UButton
            >
          </div>
          <UButton
            color="neutral"
            variant="soft"
            @click="
              option.values.push({ value_id: '', default_quantity: null })
            "
            >{{ p.addAllowed }}</UButton
          ><UButton
            color="neutral"
            variant="soft"
            @click="draft.options.splice(index, 1)"
            >{{ p.remove }} {{ p.definition }}</UButton
          >
        </section>
        <label
          >{{ p.definition
          }}<select v-model="definition">
            <option value="">{{ p.choose }}</option>
            <option
              v-for="row in catalog.definitions.filter(
                (entry) =>
                  !draft.options.some(
                    (option) => option.definition_id === entry.id,
                  ),
              )"
              :key="row.id"
              :value="row.id"
            >
              {{ row.name }}{{ row.active ? "" : ` (${p.inactiveLabel})` }}
            </option>
          </select></label
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="!definition"
          @click="add"
          >{{ p.addOption }}</UButton
        >
        <UButton type="submit" :loading="busy">{{ p.saveOptions }}</UButton>
      </fieldset>
    </form>
    <details>
      <summary>{{ p.catalog }}</summary>
      <div class="catalog-columns">
        <form class="asset-form" @submit.prevent="createDefinition">
          <h3>{{ p.newDefinition }}</h3>
          <label
            >{{ p.definitionName
            }}<input
              v-model="definitionName"
              required
              maxlength="255"
              :disabled="busy" /></label
          ><UButton type="submit" :disabled="busy">{{
            p.createDefinition
          }}</UButton>
        </form>
        <form class="asset-form" @submit.prevent="createValue">
          <h3>{{ p.newValue }}</h3>
          <fieldset :disabled="busy">
            <label
              >{{ p.definition
              }}<select v-model="valueDefinition" required>
                <option value="">{{ p.choose }}</option>
                <option
                  v-for="row in catalog.definitions"
                  :key="row.id"
                  :value="row.id"
                >
                  {{ row.name }}
                </option>
              </select></label
            ><label
              >{{ p.valueName
              }}<input v-model="valueName" required maxlength="255" /></label
            ><label
              >{{ p.family
              }}<select v-model="family">
                <option value="">{{ p.none }}</option>
                <option
                  v-for="row in catalog.families"
                  :key="row.id"
                  :value="row.id"
                >
                  {{ row.name }}
                </option>
              </select></label
            ><label
              >{{ p.optionalSupply
              }}<select v-model="supply">
                <option value="">{{ p.none }}</option>
                <option
                  v-for="row in catalog.supplies"
                  :key="row.id"
                  :value="row.id"
                >
                  {{ row.name }} ({{ row.base_unit }})
                </option>
              </select></label
            ><UButton type="submit">{{ p.createValue }}</UButton>
          </fieldset>
        </form>
      </div>
    </details>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <p v-if="success" role="status">{{ success }}</p>
  </section>
</template>
