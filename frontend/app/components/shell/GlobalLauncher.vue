<script setup lang="ts">
import {
  defaultLauncher,
  readLauncher,
  launcherKey,
  moveAction,
  type ActionId,
} from "~/features/launcher/preferences";
const { t } = useI18n();
const preferences = ref(defaultLauncher());
const customizeOpen = ref(false);
const persistent = ref(true);
onMounted(() => {
  try {
    preferences.value = readLauncher(localStorage);
  } catch {
    persistent.value = false;
  }
});
function save() {
  try {
    localStorage.setItem(launcherKey, JSON.stringify(preferences.value));
    persistent.value = true;
  } catch {
    persistent.value = false;
  }
}
function move(id: ActionId, offset: -1 | 1) {
  preferences.value = moveAction(preferences.value, id, offset);
  save();
}
const items = computed(() => [
  preferences.value.actions
    .filter((action) => action.visible)
    .map((action) => ({
      label:
        action.id === "quickQuote"
          ? t("actions.quickQuote")
          : t(`actions.${action.id}`),
      icon:
        action.id === "quickQuote" ? "i-lucide-zap" : "i-lucide-file-plus-2",
      onSelect: () =>
        action.id === "quickQuote"
          ? navigateTo("/quick-quotes/new")
          : navigateTo("/quotes/new"),
    })),
  [
    {
      label: t("actions.customize"),
      icon: "i-lucide-sliders-horizontal",
      onSelect: () => {
        customizeOpen.value = true;
      },
    },
  ],
]);
</script>
<template>
  <UDropdownMenu :items="items"
    ><UButton
      class="launcher"
      icon="i-lucide-plus"
      :aria-label="t('actions.launcher')"
  /></UDropdownMenu>
  <USlideover
    v-model:open="customizeOpen"
    :title="t('launcher.customize')"
    :description="t('launcher.description')"
  >
    <template #body
      ><div class="launcher-editor">
        <div
          v-for="(action, index) in preferences.actions"
          :key="action.id"
          class="preference-row"
        >
          <label
            ><input v-model="action.visible" type="checkbox" @change="save" />{{
              t(`actions.${action.id}`)
            }}</label
          >
          <div class="reorder-controls">
            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-arrow-up"
              :disabled="index === 0"
              :aria-label="`${t('actions.moveUp')} ${t(`actions.${action.id}`)}`"
              @click="move(action.id, -1)"
            />
            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-arrow-down"
              :disabled="index === preferences.actions.length - 1"
              :aria-label="`${t('actions.moveDown')} ${t(`actions.${action.id}`)}`"
              @click="move(action.id, 1)"
            />
          </div>
        </div>
        <p class="preference-note" role="status">
          {{ t(persistent ? "preferences.local" : "preferences.memory") }}
        </p>
      </div></template
    >
  </USlideover>
</template>
