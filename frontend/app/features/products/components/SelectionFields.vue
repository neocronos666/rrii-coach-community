<script setup lang="ts">
import type { Schema, Configuration } from "../api";
import type { Catalog } from "../useCatalog";
import { productMessages as p } from "~/i18n/products";
const model = defineModel<Schema["SelectionCondition"]>({ required: true });
defineProps<{ catalog: Catalog; configuration: Configuration }>();
</script>
<template>
  <div class="catalog-row">
    <label
      >{{ p.definition
      }}<select
        v-model="model.definition_id"
        required
        @change="model.value_id = ''"
      >
        <option value="">{{ p.choose }}</option>
        <option
          v-for="option in configuration.options"
          :key="option.definition_id"
          :value="option.definition_id"
        >
          {{
            catalog.definitions.find((row) => row.id === option.definition_id)
              ?.name || option.definition_id
          }}
        </option>
      </select></label
    ><label
      >{{ p.value
      }}<select v-model="model.value_id" required>
        <option value="">{{ p.choose }}</option>
        <option
          v-for="value in configuration.options.find(
            (row) => row.definition_id === model.definition_id,
          )?.values ?? []"
          :key="value.value_id"
          :value="value.value_id"
        >
          {{
            catalog.values.find((row) => row.id === value.value_id)?.name ||
            value.value_id
          }}
        </option>
      </select></label
    >
  </div>
</template>
