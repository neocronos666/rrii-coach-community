<script setup lang="ts">
import { es } from "@nuxt/ui/locale";
useHead({ htmlAttrs: { lang: "es" }, title: "RRII-Coach Community" });
</script>
<template>
  <UApp :locale="es"
    ><NuxtRouteAnnouncer /><ShellAppShell><NuxtPage /></ShellAppShell
  ></UApp>
</template>
