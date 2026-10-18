<script setup lang="ts">
import { inventoryMessages as i } from "~/i18n/inventory";
defineProps<{
  stock: {
    physical_quantity: string;
    available_quantity: string;
    reserved_quantity?: string;
    allocated_quantity?: string;
    unit: string;
    shortage_warning: boolean;
  };
}>();
</script>
<template>
  <section
    class="asset-panel asset-form"
    aria-label="Existencias"
    data-testid="stock-summary"
  >
    <dl>
      <dt>{{ i.physical }}</dt>
      <dd data-testid="physical">
        {{ stock.physical_quantity }} {{ stock.unit }}
      </dd>
      <dt v-if="stock.reserved_quantity !== undefined">{{ i.reserved }}</dt>
      <dd v-if="stock.reserved_quantity !== undefined" data-testid="reserved">
        {{ stock.reserved_quantity }} {{ stock.unit }}
      </dd>
      <dt v-if="stock.allocated_quantity !== undefined">{{ i.allocated }}</dt>
      <dd v-if="stock.allocated_quantity !== undefined" data-testid="allocated">
        {{ stock.allocated_quantity }} {{ stock.unit }}
      </dd>
      <dt>{{ i.available }}</dt>
      <dd data-testid="available">
        {{ stock.available_quantity }} {{ stock.unit }}
      </dd>
    </dl>
    <p v-if="stock.shortage_warning" role="status">{{ i.shortage }}</p>
  </section>
</template>
