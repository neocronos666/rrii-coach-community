<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { commercialApi } from "./api";
import { ApiError, errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
import { productionMessages as p } from "~/i18n/production";
import { commercialMessages as c } from "~/i18n/commercial";
const props = defineProps<{ kind: "orders" | "projects"; id: string }>();
const api = commercialApi(useRuntimeConfig().public.apiBaseUrl),
  cache = useQueryClient();
const query = useQuery({
  queryKey: [props.kind, props.id],
  queryFn: async () =>
    props.kind === "orders" ? api.order(props.id) : api.project(props.id),
  retry: false,
});
const record = computed(() => query.data.value);
const components = computed(() => {
  const row = record.value;
  return !row ? [] : "components" in row ? row.components : [row];
});
const technical = computed(() => {
  const row = record.value;
  return !row
    ? ""
    : "quoted_technical_cost" in row
      ? row.quoted_technical_cost
      : row.technical_total_cost;
});
const confirmed = ref(false),
  busy = ref(false),
  error = ref("");
async function cancel() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    if (props.kind === "orders") await api.cancelOrder(props.id);
    else await api.cancelProject(props.id);
    confirmed.value = false;
  } catch (failure) {
    error.value = errorMessage(failure);
    if (
      !(failure instanceof ApiError) ||
      failure.status >= 500 ||
      failure.status === 408
    )
      error.value += ` ${c.uncertain}`;
  } finally {
    await cache.invalidateQueries({ queryKey: [props.kind] });
    busy.value = false;
  }
}
useHead(() => ({
  title: `${record.value?.code || c[props.kind]} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton :to="`/${kind}`" color="neutral" variant="soft">{{
      c[kind]
    }}</UButton>
    <p v-if="query.isPending.value" role="status">{{ c.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ c.retry }}</UButton>
    </div>
    <template v-if="record">
      <h1>{{ record.code }} · {{ record.title }}</h1>
      <p>{{ c.snapshot }}</p>
      <p>{{ record.description }}</p>
      <p data-testid="destination-status">
        {{ record.status === "pending" ? c.pending : c.cancelled }}
      </p>
      <section class="asset-panel">
        <h2>{{ c.total }}</h2>
        <p data-testid="destination-total">
          {{ record.currency }} {{ record.quoted_final_price }}
        </p>
        <dl>
          <dt>{{ c.technical }}</dt>
          <dd>{{ record.currency }} {{ technical }}</dd>
          <dt>{{ c.suggested }}</dt>
          <dd>{{ record.currency }} {{ record.quoted_suggested_price }}</dd>
        </dl>
      </section>
      <section class="asset-panel">
        <h2>{{ c.components }}</h2>
        <ul>
          <li v-for="row in components" :key="row.id">
            <h3>{{ row.description }}</h3>
            <p>{{ c.quantity }}: {{ row.quantity }}</p>
            <p>
              {{ c.technical }}: {{ record.currency }}
              {{ row.technical_total_cost }}
            </p>
            <p>{{ row.notes }}</p>
            <div class="asset-actions">
              <UButton
                v-if="record.status === 'pending'"
                :to="
                  kind === 'orders'
                    ? `/production/tasks/new?order=${record.id}`
                    : `/production/tasks/new?project=${record.id}&component=${row.id}`
                "
                >Crear tarea manual</UButton
              >
              <UButton
                :to="
                  kind === 'orders'
                    ? `/inventory/allocations?order=${record.id}`
                    : `/inventory/allocations?project=${record.id}&component=${row.id}`
                "
                color="neutral"
                variant="soft"
                >{{ i.allocations }}</UButton
              >
              <UButton
                v-if="record.status === 'pending'"
                :to="
                  kind === 'orders'
                    ? `/production/plans/new?order=${record.id}`
                    : `/production/plans/new?project=${record.id}&component=${row.id}`
                "
                >{{ p.planLinkNew }}</UButton
              >
              <UButton
                :to="
                  kind === 'orders'
                    ? `/production?order=${record.id}`
                    : `/production?component=${row.id}`
                "
                color="neutral"
                variant="soft"
                >{{ p.productionLink }}</UButton
              >
            </div>
          </li>
        </ul>
      </section>
      <p>{{ record.notes }}</p>
      <UButton
        :to="`/quotes/${record.source_quote_id}`"
        color="neutral"
        variant="soft"
        >{{ c.source }}</UButton
      >
      <p v-if="error" role="alert">{{ error }}</p>
      <form
        v-if="record.status === 'pending'"
        class="asset-panel asset-form"
        @submit.prevent="cancel"
      >
        <p>{{ c.cancelHelp }}</p>
        <fieldset :disabled="busy">
          <label class="catalog-check"
            ><input v-model="confirmed" type="checkbox" required />{{
              c.cancelConfirm
            }}</label
          ><UButton
            type="submit"
            color="neutral"
            variant="soft"
            :disabled="!confirmed"
            >{{ c.cancel }}</UButton
          >
        </fieldset>
      </form>
    </template>
  </div>
</template>
