<script setup lang="ts">
import OptionList from "~/features/options/OptionList.vue";
useHead({ title: "Opciones y valores · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>Opciones y valores</h1>
    <p>
      Características y valores reutilizables. La configuración permitida y sus
      cantidades se editan desde cada producto.
    </p>
    <OptionList />
  </div>
</template>
