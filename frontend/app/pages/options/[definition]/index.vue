<script setup lang="ts">
import OptionPage from "~/features/options/OptionPage.vue";
definePageMeta({ key: (route) => route.path });
const definition = String(useRoute().params.definition);
</script>
<template><OptionPage :definition="definition" /></template>
