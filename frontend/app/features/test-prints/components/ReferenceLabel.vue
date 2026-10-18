<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "~/features/products/api";
import { testPrintMessages as t } from "~/i18n/test-prints";
const props = defineProps<{ id: string; kind: "variant" | "supply" }>();
const api = productApi(useRuntimeConfig().public.apiBaseUrl);
const variant = useQuery({
  queryKey: computed(() => ["test-reference-variant", props.id]),
  queryFn: () => api.variant(props.id),
  enabled: computed(() => props.kind === "variant"),
  retry: false,
});
const supplies = useQuery({
  queryKey: ["test-reference-supplies"],
  queryFn: api.supplies,
  enabled: computed(() => props.kind === "supply"),
  retry: false,
});
const name = computed(() =>
  props.kind === "variant"
    ? variant.data.value?.name
    : supplies.data.value?.find((row) => row.id === props.id)?.name,
);
</script>
<template>
  <span
    ><template v-if="name">{{ t.currentName }}: {{ name }} · </template
    >{{ id }}</span
  >
</template>
