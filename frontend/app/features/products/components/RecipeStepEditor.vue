<script setup lang="ts">
import type { Step, ProductApi, Configuration } from "../api";
import type { Catalog } from "../useCatalog";
import { units, taskTypes, machineTypes } from "../drafts";
import {
  productMessages as p,
  taskLabels,
  machineLabels,
} from "~/i18n/products";
import SelectionFields from "./SelectionFields.vue";
import RevisionPicker from "./RevisionPicker.vue";
import VariantPicker from "./VariantPicker.vue";
const step = defineModel<Step>({ required: true });
const props = defineProps<{
  api: ProductApi;
  catalog: Catalog;
  configuration: Configuration;
  steps: Step[];
  assetHints: Record<string, string>;
}>();
// Identidades sólo de presentación: al quitar una fila no se reutiliza su selector.
const rowKeys = new WeakMap<object, number>();
let nextRowKey = 0;
function rowKey(row: object) {
  const raw = toRaw(row);
  if (!rowKeys.has(raw)) rowKeys.set(raw, ++nextRowKey);
  return rowKeys.get(raw)!;
}
const contexts = [
  ["piece", "contextPiece"],
  ["design", "contextDesign"],
  ["product", "contextProduct"],
  ["quantity", "contextQuantity"],
] as const;
function context(key: string, value: string) {
  if (!step.value.action_context) step.value.action_context = {};
  if (value) step.value.action_context[key] = value;
  else delete step.value.action_context[key];
}
function addResource(selected: boolean) {
  step.value.resources ??= [];
  let number = step.value.resources.length + 1;
  while (step.value.resources.some((row) => row.key === `resource_${number}`))
    number++;
  const key = `resource_${number}`;
  step.value.resources.push(
    selected
      ? {
          key,
          from_selection: { definition_id: "", value_id: "" },
          quantity_per_batch: "1",
          label: null,
        }
      : { key, asset_revision_id: "", quantity_per_batch: "1", label: null },
  );
}
</script>
<template>
  <div class="asset-form">
    <div class="catalog-row">
      <label
        >{{ p.key
        }}<input
          v-model="step.key"
          required
          pattern="[a-z][a-z0-9_]{0,79}" /></label
      ><label
        >{{ p.stepTitle }}<input v-model="step.title" required maxlength="255"
      /></label>
    </div>
    <div class="catalog-row">
      <label
        >{{ p.kind
        }}<select v-model="step.kind">
          <option value="operation">{{ p.operation }}</option>
          <option value="print">{{ p.print }}</option>
          <option value="service">{{ p.service }}</option>
          <option value="wait">{{ p.wait }}</option>
        </select></label
      ><label
        >{{ p.taskType
        }}<select v-model="step.task_type">
          <option v-for="kind in taskTypes" :key="kind" :value="kind">
            {{ taskLabels[kind] }}
          </option>
        </select></label
      >
    </div>
    <div class="catalog-row">
      <label
        >{{ p.unit
        }}<select v-model="step.unit">
          <option v-for="unit in units" :key="unit" :value="unit">
            {{ unit }}
          </option>
        </select></label
      ><label
        >{{ p.perOutput
        }}<input
          v-model="step.quantity_per_output"
          inputmode="decimal"
          required /></label
      ><label
        >{{ p.yield
        }}<input v-model="step.batch_yield" inputmode="decimal" required
      /></label>
    </div>
    <label class="catalog-check"
      ><input v-model="step.is_final_output" type="checkbox" />{{
        p.final
      }}</label
    >
    <VariantPicker
      v-model="step.output_variant_id"
      :api="api"
      :products="catalog.products"
      :label="p.output"
      optional
    />
    <label
      >{{ p.machineType
      }}<select v-model="step.required_machine_type">
        <option :value="null">{{ p.none }}</option>
        <option v-for="kind in machineTypes" :key="kind" :value="kind">
          {{ machineLabels[kind] }}
        </option>
      </select></label
    >
    <label>{{ p.instructions }}<textarea v-model="step.instructions" /></label>
    <fieldset>
      <legend>{{ p.dependencies }}</legend>
      <label
        v-for="other in steps.filter((row) => row !== step)"
        :key="other.key"
        class="catalog-check"
        ><input
          v-model="step.depends_on"
          type="checkbox"
          :value="other.key"
        />{{ other.title || other.key }}</label
      >
      <label
        v-for="key in (step.depends_on ?? []).filter(
          (key) => !steps.some((row) => row.key === key),
        )"
        :key="key"
        class="catalog-check"
        ><input v-model="step.depends_on" type="checkbox" :value="key" />{{
          p.missingDependency
        }}: {{ key }}</label
      >
      <p v-if="!steps.filter((row) => row !== step).length">{{ p.none }}</p>
    </fieldset>
    <label class="catalog-check"
      ><input
        type="checkbox"
        :checked="!!step.when_selected"
        @change="
          step.when_selected = ($event.target as HTMLInputElement).checked
            ? { definition_id: '', value_id: '' }
            : null
        "
      />{{ p.condition }}</label
    >
    <SelectionFields
      v-if="step.when_selected"
      v-model="step.when_selected"
      :catalog="catalog"
      :configuration="configuration"
    />
    <label class="catalog-check"
      ><input v-model="step.scale_by_selection" type="checkbox" />{{
        p.scale
      }}</label
    >
    <details :open="step.kind === 'service'">
      <summary>{{ p.service }}</summary>
      <div class="asset-form">
        <label
          >{{ p.serviceDefinition
          }}<select v-model="step.service_definition_id">
            <option :value="null">{{ p.none }}</option>
            <option
              v-for="service in catalog.services"
              :key="service.id"
              :value="service.id"
            >
              {{ service.name
              }}{{ service.active ? "" : ` (${p.inactiveLabel})` }}
            </option>
          </select></label
        ><label
          >{{ p.actionTemplate
          }}<textarea
            :value="step.action_template ?? ''"
            @input="
              step.action_template =
                ($event.target as HTMLTextAreaElement).value || null
            "
          />
        </label>
        <p>{{ p.actionHelp }}</p>
        <label v-for="[key, label] in contexts" :key="key"
          >{{ p[label]
          }}<input
            :value="step.action_context?.[key] ?? ''"
            maxlength="1000"
            @input="context(key, ($event.target as HTMLInputElement).value)"
        /></label>
      </div>
    </details>
    <details>
      <summary>{{ p.resources }} ({{ step.resources?.length ?? 0 }})</summary>
      <div class="asset-form">
        <section
          v-for="(resource, index) in step.resources"
          :key="rowKey(resource)"
          class="catalog-group asset-form"
        >
          <h4>
            {{
              "from_selection" in resource
                ? p.selectedResource
                : p.fixedResource
            }}
          </h4>
          <label
            >{{ p.resourceKey
            }}<input
              v-model="resource.key"
              required
              pattern="[a-z][a-z0-9_]{0,79}" /></label
          ><label
            >{{ p.resourceLabel
            }}<input
              :value="resource.label ?? ''"
              @input="
                resource.label =
                  ($event.target as HTMLInputElement).value || null
              " /></label
          ><SelectionFields
            v-if="'from_selection' in resource"
            v-model="resource.from_selection"
            :catalog="catalog"
            :configuration="configuration"
          /><RevisionPicker
            v-else
            v-model="resource.asset_revision_id"
            :api="api"
            :assets="catalog.assets"
            :asset-hint="assetHints[resource.asset_revision_id]"
          /><label
            >{{ p.perBatch
            }}<input
              v-model="resource.quantity_per_batch"
              inputmode="decimal"
              required /></label
          ><UButton
            color="neutral"
            variant="soft"
            @click="step.resources?.splice(index, 1)"
            >{{ p.remove }} {{ p.asset }}</UButton
          >
        </section>
        <div class="asset-actions">
          <UButton color="neutral" variant="soft" @click="addResource(false)">{{
            p.addFixed
          }}</UButton
          ><UButton color="neutral" variant="soft" @click="addResource(true)">{{
            p.addSelected
          }}</UButton>
        </div>
      </div>
    </details>
    <details>
      <summary>
        {{ p.fixedMaterials }} ({{ step.supply_inputs?.length ?? 0 }})
      </summary>
      <div class="asset-form">
        <div
          v-for="(input, index) in step.supply_inputs"
          :key="index"
          class="catalog-group asset-form"
        >
          <label
            >{{ p.supply
            }}<select v-model="input.supply_id" required>
              <option value="">{{ p.choose }}</option>
              <option
                v-for="row in catalog.supplies"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }} ({{ row.base_unit }})
              </option>
            </select></label
          ><label
            >{{ p.perBatch
            }}<input
              v-model="input.quantity_per_batch"
              inputmode="decimal"
              required /></label
          ><UButton
            color="neutral"
            variant="soft"
            @click="step.supply_inputs?.splice(index, 1)"
            >{{ p.remove }} {{ p.supply }}</UButton
          >
        </div>
        <UButton
          color="neutral"
          variant="soft"
          @click="
            (step.supply_inputs ??= []).push({
              supply_id: '',
              quantity_per_batch: '1',
            })
          "
          >{{ p.addMaterial }}</UButton
        >
      </div>
    </details>
    <details>
      <summary>
        {{ p.selectedMaterials }} ({{
          step.selected_supply_inputs?.length ?? 0
        }})
      </summary>
      <div class="asset-form">
        <div
          v-for="(input, index) in step.selected_supply_inputs"
          :key="index"
          class="catalog-group asset-form"
        >
          <label
            >{{ p.definition
            }}<select v-model="input.definition_id" required>
              <option value="">{{ p.choose }}</option>
              <option
                v-for="option in configuration.options"
                :key="option.definition_id"
                :value="option.definition_id"
              >
                {{
                  catalog.definitions.find(
                    (row) => row.id === option.definition_id,
                  )?.name || option.definition_id
                }}
              </option>
            </select></label
          ><label
            >{{ p.unit
            }}<select v-model="input.unit">
              <option v-for="unit in units" :key="unit" :value="unit">
                {{ unit }}
              </option>
            </select></label
          ><label
            >{{ p.perBatch
            }}<input
              v-model="input.quantity_per_batch"
              inputmode="decimal"
              required /></label
          ><UButton
            color="neutral"
            variant="soft"
            @click="step.selected_supply_inputs?.splice(index, 1)"
            >{{ p.remove }} {{ p.supply }}</UButton
          >
        </div>
        <UButton
          color="neutral"
          variant="soft"
          @click="
            (step.selected_supply_inputs ??= []).push({
              definition_id: '',
              unit: 'unit',
              quantity_per_batch: '1',
            })
          "
          >{{ p.addSelectedMaterial }}</UButton
        >
      </div>
    </details>
    <details>
      <summary>
        {{ p.productInputs }} ({{ step.product_inputs?.length ?? 0 }})
      </summary>
      <div class="asset-form">
        <div
          v-for="(input, index) in step.product_inputs"
          :key="index"
          class="catalog-group asset-form"
        >
          <VariantPicker
            v-model="input.product_variant_id"
            :api="api"
            :products="catalog.products"
            :label="p.inputVariant"
          /><label
            >{{ p.perBatch
            }}<input
              v-model="input.quantity_per_batch"
              inputmode="decimal"
              required /></label
          ><label
            >{{ p.sourceStep
            }}<select v-model="input.source_step_key">
              <option :value="null">{{ p.none }}</option>
              <option
                v-for="other in steps"
                :key="other.key"
                :value="other.key"
              >
                {{ other.title || other.key }}
              </option>
            </select></label
          ><UButton
            color="neutral"
            variant="soft"
            @click="step.product_inputs?.splice(index, 1)"
            >{{ p.remove }} {{ p.inputProduct }}</UButton
          >
        </div>
        <UButton
          color="neutral"
          variant="soft"
          @click="
            (step.product_inputs ??= []).push({
              product_variant_id: '',
              quantity_per_batch: '1',
              source_step_key: null,
            })
          "
          >{{ p.addProductInput }}</UButton
        >
      </div>
    </details>
    <details v-if="Object.keys(step.parameters ?? {}).length">
      <summary>{{ p.storedParameters }}</summary>
      <p>{{ p.parametersHelp }}</p>
      <dl>
        <template v-for="(value, key) in step.parameters" :key="key"
          ><dt>{{ key }}</dt>
          <dd>{{ value }}</dd></template
        >
      </dl>
    </details>
  </div>
</template>
