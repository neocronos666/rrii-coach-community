<script setup lang="ts">
import OptionPage from "~/features/options/OptionPage.vue";
definePageMeta({ key: (route) => route.path });
const route = useRoute(),
  definition = String(route.params.definition),
  value = String(route.params.value);
</script>
<template><OptionPage :definition="definition" :value="value" /></template>
