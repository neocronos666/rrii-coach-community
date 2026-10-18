<script setup lang="ts">
import DashboardBlock from "./DashboardBlock.vue";
import { useDashboardPreferences } from "../useDashboardPreferences";
import { supportsSummary, type BlockPreference } from "../preferences";
const { t } = useI18n();
useHead(() => ({ title: `${t("navigation.home")} · ${t("brand.name")}` }));
const {
  preferences,
  persistent,
  visibleBlocks,
  update,
  move,
  moveVisible,
  reset,
} = useDashboardPreferences();
const customizeOpen = ref(false);
const toast = useToast();
function contextualItems(block: BlockPreference) {
  const index = visibleBlocks.value.findIndex((item) => item.id === block.id);
  return [
    [
      ...(supportsSummary(block.id)
        ? [
            {
              label: t(
                block.view === "list"
                  ? "dashboard.showSummary"
                  : "dashboard.showList",
              ),
              icon: "i-lucide-list",
              onSelect: () =>
                update(block.id, {
                  view: block.view === "list" ? "summary" : "list",
                }),
            },
          ]
        : []),
      {
        label: t(
          block.size === "standard"
            ? "dashboard.widen"
            : "dashboard.standardSize",
        ),
        icon: "i-lucide-columns-2",
        onSelect: () =>
          update(block.id, {
            size: block.size === "standard" ? "wide" : "standard",
          }),
      },
      {
        label: t("actions.moveUp"),
        icon: "i-lucide-arrow-up",
        disabled: index === 0,
        onSelect: () => moveVisible(block.id, -1),
      },
      {
        label: t("actions.moveDown"),
        icon: "i-lucide-arrow-down",
        disabled: index === visibleBlocks.value.length - 1,
        onSelect: () => moveVisible(block.id, 1),
      },
    ],
    [
      {
        label: t("actions.hide"),
        icon: "i-lucide-eye-off",
        onSelect: () => {
          update(block.id, { visible: false });
          nextTick(() =>
            requestAnimationFrame(() =>
              document
                .querySelector<HTMLButtonElement>("[data-customize-dashboard]")
                ?.focus(),
            ),
          );
        },
      },
      {
        label: t("actions.customize"),
        icon: "i-lucide-sliders-horizontal",
        onSelect: () => {
          customizeOpen.value = true;
        },
      },
    ],
  ];
}
function restore() {
  reset();
  toast.add({ title: t("dashboard.restored"), icon: "i-lucide-check" });
}
</script>
<template>
  <div class="dashboard-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">{{ t("dashboard.eyebrow") }}</p>
        <h1>{{ t("dashboard.title") }}</h1>
        <p class="page-description">{{ t("dashboard.description") }}</p>
      </div>
      <div class="page-header-tools">
        <UButton
          data-customize-dashboard
          color="neutral"
          variant="ghost"
          icon="i-lucide-sliders-horizontal"
          @click="customizeOpen = true"
          >{{ t("dashboard.customize") }}</UButton
        >
      </div>
    </header>
    <p class="preference-note">
      Datos de la instalación conectada. Cada bloque informa su consulta y
      permite actualizarla.
    </p>
    <div v-if="visibleBlocks.length" class="dashboard-grid">
      <section
        v-for="block in visibleBlocks"
        :key="block.id"
        class="dashboard-block"
        :class="[`block-${block.id}`, { 'block-wide': block.size === 'wide' }]"
        :data-block="block.id"
        :aria-labelledby="`heading-${block.id}`"
      >
        <header class="section-header">
          <h2 :id="`heading-${block.id}`">{{ t(`dashboard.${block.id}`) }}</h2>
          <UDropdownMenu :items="contextualItems(block)"
            ><UButton
              class="context-control"
              color="neutral"
              variant="ghost"
              icon="i-lucide-ellipsis"
              :aria-label="`${t('dashboard.options')} ${t(`dashboard.${block.id}`)}`"
          /></UDropdownMenu>
        </header>
        <DashboardBlock :id="block.id" :view="block.view" />
      </section>
    </div>
    <section v-else class="dashboard-empty">
      <UIcon name="i-lucide-layout-dashboard" aria-hidden="true" />
      <h2>{{ t("dashboard.emptyTitle") }}</h2>
      <p>{{ t("dashboard.emptyDescription") }}</p>
      <UButton variant="soft" @click="customizeOpen = true">{{
        t("dashboard.chooseBlocks")
      }}</UButton>
    </section>
  </div>
  <USlideover
    v-model:open="customizeOpen"
    :title="t('dashboard.customize')"
    :description="t('dashboard.customizeDescription')"
    :ui="{ content: 'dashboard-editor-panel' }"
  >
    <template #body
      ><div class="dashboard-editor">
        <fieldset
          v-for="(block, index) in preferences.blocks"
          :key="block.id"
          class="block-preference"
        >
          <legend>{{ t(`dashboard.${block.id}`) }}</legend>
          <div class="preference-row">
            <label
              ><input
                type="checkbox"
                :checked="block.visible"
                @change="
                  update(block.id, {
                    visible: ($event.target as HTMLInputElement).checked,
                  })
                "
              />{{ t("dashboard.showBlock") }}</label
            >
            <div class="reorder-controls">
              <UButton
                color="neutral"
                variant="ghost"
                icon="i-lucide-arrow-up"
                :disabled="index === 0"
                :aria-label="`${t('actions.moveUp')} ${t(`dashboard.${block.id}`)}`"
                @click="move(block.id, -1)"
              /><UButton
                color="neutral"
                variant="ghost"
                icon="i-lucide-arrow-down"
                :disabled="index === preferences.blocks.length - 1"
                :aria-label="`${t('actions.moveDown')} ${t(`dashboard.${block.id}`)}`"
                @click="move(block.id, 1)"
              />
            </div>
          </div>
          <div class="block-preference-options">
            <label :for="`size-${block.id}`"
              >{{ t("dashboard.size")
              }}<select
                :id="`size-${block.id}`"
                :aria-label="`${t('dashboard.size')} ${t(`dashboard.${block.id}`)}`"
                :value="block.size"
                @change="
                  update(block.id, {
                    size: ($event.target as HTMLSelectElement)
                      .value as BlockPreference['size'],
                  })
                "
              >
                <option value="standard">
                  {{ t("dashboard.standardSize") }}
                </option>
                <option value="wide">{{ t("dashboard.wideSize") }}</option>
              </select></label
            >
            <label v-if="supportsSummary(block.id)" :for="`view-${block.id}`"
              >{{ t("dashboard.view")
              }}<select
                :id="`view-${block.id}`"
                :aria-label="`${t('dashboard.view')} ${t(`dashboard.${block.id}`)}`"
                :value="block.view"
                @change="
                  update(block.id, {
                    view: ($event.target as HTMLSelectElement)
                      .value as BlockPreference['view'],
                  })
                "
              >
                <option value="list">{{ t("dashboard.listView") }}</option>
                <option value="summary">
                  {{ t("dashboard.summaryView") }}
                </option>
              </select></label
            >
          </div>
        </fieldset>
        <p class="preference-note" role="status">
          {{ t(persistent ? "preferences.local" : "preferences.memory") }}
        </p>
      </div></template
    >
    <template #footer
      ><UButton
        color="neutral"
        variant="soft"
        icon="i-lucide-rotate-ccw"
        @click="restore"
        >{{ t("dashboard.restore") }}</UButton
      ><UButton @click="customizeOpen = false">{{
        t("actions.done")
      }}</UButton></template
    >
  </USlideover>
</template>
