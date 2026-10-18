<script setup lang="ts">
import DestinationDetail from "~/features/commercial/DestinationDetail.vue";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id);
</script>
<template><DestinationDetail kind="projects" :id="id" /></template>
