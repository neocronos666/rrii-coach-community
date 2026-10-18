<script setup lang="ts">
import type { Schema } from "../api";
import { units } from "../drafts";
import { productMessages as p } from "~/i18n/products";
const model = defineModel<Schema["VariantCreate"]>({ required: true });
const props = defineProps<{ existing?: boolean }>();
const attributeName = ref(""),
  attributeValue = ref("");
function addAttribute() {
  if (attributeName.value && attributeValue.value) {
    model.value.attributes = {
      ...model.value.attributes,
      [attributeName.value]: attributeValue.value,
    };
    attributeName.value = "";
    attributeValue.value = "";
  }
}
</script>
<template>
  <div class="asset-form">
    <label
      >{{ p.variantName }}<input v-model="model.name" required maxlength="255"
    /></label>
    <label
      >{{ p.sku
      }}<input
        :value="model.sku ?? ''"
        maxlength="100"
        @input="model.sku = ($event.target as HTMLInputElement).value || null"
    /></label>
    <label>{{ p.description }}<textarea v-model="model.description" /></label>
    <label
      >{{ p.unit
      }}<select v-model="model.base_unit" :disabled="props.existing">
        <option v-for="unit in units" :key="unit" :value="unit">
          {{ unit }}
        </option>
      </select></label
    >
    <p v-if="existing">{{ p.immutableUnit }}</p>
    <label class="catalog-check"
      ><input v-model="model.active" type="checkbox" />{{ p.active }}</label
    >
    <details>
      <summary>{{ p.attributes }}</summary>
      <div class="asset-form">
        <div
          v-for="(value, key) in model.attributes"
          :key="key"
          class="catalog-row"
        >
          <label
            >{{ key }}<input v-model="model.attributes![key]" required /></label
          ><UButton
            color="neutral"
            variant="soft"
            @click="delete model.attributes![key]"
            >{{ p.remove }} {{ key }}</UButton
          >
        </div>
        <label
          >{{ p.attributeName
          }}<input v-model="attributeName" maxlength="100" /></label
        ><label
          >{{ p.attributeValue
          }}<input v-model="attributeValue" maxlength="255" /></label
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="!attributeName || !attributeValue"
          @click="addAttribute"
          >{{ p.addAttribute }}</UButton
        >
      </div>
    </details>
  </div>
</template>
