<script setup lang="ts">
const section = String(useRoute().params.section);
if (section === "supplies") await navigateTo("/inventory", { replace: true });
else
  throw createError({ statusCode: 404, statusMessage: "Página no encontrada" });
</script>
<template>
  <div><NuxtLink to="/">Volver al inicio</NuxtLink></div>
</template>
