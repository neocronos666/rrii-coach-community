<script setup lang="ts">
import type { MessageKey } from "~/i18n/es";
const { t } = useI18n();
const { mode, setMode, toggle } = useAppearance();
const {
  preferences,
  persistent,
  update: updateDevice,
} = useDevicePreferences();
const search = ref("");
const collapsed = ref(false);
const settingsOpen = ref(false);
const route = useRoute();
watch(
  () => route.fullPath,
  () => {
    search.value = "";
    nextTick(() => document.getElementById("main-content")?.focus());
  },
);
const links: { key: MessageKey; to: string; icon: string }[] = [
  { key: "navigation.home", to: "/", icon: "i-lucide-house" },
  { key: "navigation.quotes", to: "/quotes", icon: "i-lucide-file-text" },
  { key: "navigation.production", to: "/production", icon: "i-lucide-layers" },
  { key: "navigation.products", to: "/products", icon: "i-lucide-box" },
  {
    key: "navigation.inventory",
    to: "/inventory",
    icon: "i-lucide-package-open",
  },
  { key: "navigation.assets", to: "/assets", icon: "i-lucide-component" },
];
// Biblioteca también está disponible en Más para mobile.
const moreItems = computed(() => [
  {
    label: t("navigation.families"),
    to: "/families",
    icon: "i-lucide-component",
  },
  { label: t("navigation.options"), to: "/options", icon: "i-lucide-layers" },
  { label: t("navigation.services"), to: "/services", icon: "i-lucide-layers" },
  { label: t("navigation.assets"), to: "/assets", icon: "i-lucide-component" },
  {
    label: t("navigation.inventory"),
    to: "/inventory",
    icon: "i-lucide-package-open",
  },
  {
    label: t("navigation.machines"),
    to: "/machines",
    icon: "i-lucide-printer",
  },
  {
    label: t("navigation.installation"),
    to: "/settings",
    icon: "i-lucide-settings-2",
  },
  { label: t("navigation.supplies"), to: "/inventory", icon: "i-lucide-spool" },
  {
    label: t("navigation.settings"),
    icon: "i-lucide-settings-2",
    onSelect: () => {
      settingsOpen.value = true;
    },
  },
]);
const searchResults = computed(() => {
  const entries = [
    ...links.map((row) => ({ label: t(row.key), to: row.to })),
    ...moreItems.value
      .filter((row) => row.to)
      .map((row) => ({ label: row.label, to: row.to! })),
    { label: "Quick Quote · borradores", to: "/quick-quotes" },
    { label: "Test Print", to: "/test-prints" },
    { label: "Pedidos", to: "/orders" },
    { label: "Proyectos", to: "/projects" },
    { label: "Categorías de Assets", to: "/asset-categories" },
    { label: "Cálculo técnico", to: "/calculations/new" },
  ];
  const needle = search.value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  return entries
    .filter((row) =>
      row.label
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .includes(needle),
    )
    .filter(
      (row, index, matches) =>
        matches.findIndex((other) => other.to === row.to) === index,
    );
});
</script>
<template>
  <a class="skip-link" href="#main-content">{{ t("navigation.skip") }}</a>
  <div class="app-shell" :class="{ 'is-collapsed': collapsed }">
    <header class="topbar">
      <NuxtLink to="/" class="brand"
        ><span class="brand-mark" aria-hidden="true">R<span>·</span></span
        ><span
          >{{ t("brand.name") }}<small>{{ t("brand.edition") }}</small></span
        ></NuxtLink
      >
      <div class="search-area">
        <label class="sr-only" for="global-search">{{
          "Buscar sección"
        }}</label>
        <div class="search-input">
          <UIcon name="i-lucide-search" /><input
            id="global-search"
            placeholder="Buscar sección"
            v-model="search"
            type="search"
            @keydown.esc="search = ''"
          />
        </div>
        <nav
          v-if="search.trim()"
          class="section-search-results"
          aria-label="Resultados de secciones"
        >
          <ul v-if="searchResults.length">
            <li v-for="row in searchResults" :key="row.to">
              <NuxtLink :to="row.to">{{ row.label }}</NuxtLink>
            </li>
          </ul>
          <p v-else role="status">No hay secciones con ese nombre.</p>
        </nav>
      </div>
      <div class="topbar-actions">
        <ShellGlobalLauncher />
        <UButton
          color="neutral"
          variant="ghost"
          :icon="mode === 'dark' ? 'i-lucide-sun' : 'i-lucide-moon'"
          :aria-label="t('appearance.toggle')"
          @click="toggle"
        />
        <UButton
          color="neutral"
          variant="ghost"
          icon="i-lucide-settings-2"
          :aria-label="t('navigation.settings')"
          @click="settingsOpen = true"
        />
      </div>
    </header>
    <aside class="sidebar">
      <nav :aria-label="t('navigation.main')">
        <NuxtLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          :aria-current="route.path === link.to ? 'page' : undefined"
          :aria-label="t(link.key)"
          :title="collapsed ? t(link.key) : undefined"
          ><UIcon :name="link.icon" /><span>{{ t(link.key) }}</span></NuxtLink
        >
        <UDropdownMenu :items="moreItems"
          ><button
            class="nav-link more-link"
            :aria-label="t('navigation.more')"
          >
            <UIcon name="i-lucide-ellipsis" /><span>{{
              t("navigation.more")
            }}</span>
          </button></UDropdownMenu
        >
      </nav>
      <button
        class="collapse-control nav-link"
        :aria-label="t(collapsed ? 'navigation.expand' : 'navigation.collapse')"
        @click="collapsed = !collapsed"
      >
        <UIcon
          :name="
            collapsed ? 'i-lucide-panel-left-open' : 'i-lucide-panel-left-close'
          "
        /><span>{{ t("navigation.collapse") }}</span>
      </button>
    </aside>
    <main id="main-content" class="main-content" tabindex="-1"><slot /></main>
    <nav class="mobile-nav" :aria-label="t('navigation.main')">
      <NuxtLink
        v-for="link in links.slice(0, 4)"
        :key="link.to"
        :to="link.to"
        :aria-label="t(link.key)"
        :aria-current="route.path === link.to ? 'page' : undefined"
        ><UIcon :name="link.icon" /><span>{{
          t(
            link.key === "navigation.quotes"
              ? "navigation.quotesCompact"
              : link.key,
          )
        }}</span></NuxtLink
      ><UDropdownMenu :items="moreItems"
        ><button>
          <UIcon name="i-lucide-ellipsis" /><span>{{
            t("navigation.more")
          }}</span>
        </button></UDropdownMenu
      >
    </nav>
  </div>
  <USlideover v-model:open="settingsOpen" :title="t('appearance.title')"
    ><template #close
      ><UButton
        color="neutral"
        variant="ghost"
        icon="i-lucide-x"
        :aria-label="t('actions.close')" /></template
    ><template #body
      ><fieldset class="device-options">
        <legend>{{ t("preferences.title") }}</legend>
        <label for="display-profile">{{ t("preferences.profile") }}</label>
        <select
          id="display-profile"
          :value="preferences.profile"
          @change="
            updateDevice({
              profile: ($event.target as HTMLSelectElement)
                .value as typeof preferences.profile,
            })
          "
        >
          <option
            v-for="value in ['auto', 'desktop', 'mobile', 'touch'] as const"
            :key="value"
            :value="value"
          >
            {{ t(`preferences.${value}`) }}
          </option>
        </select>
        <label for="display-density">{{ t("preferences.density") }}</label>
        <select
          id="display-density"
          :value="preferences.density"
          @change="
            updateDevice({
              density: ($event.target as HTMLSelectElement)
                .value as typeof preferences.density,
            })
          "
        >
          <option value="comfortable">
            {{ t("preferences.comfortable") }}
          </option>
          <option value="compact">{{ t("preferences.compact") }}</option>
        </select>
        <p class="preference-note">{{ t("preferences.densityHelp") }}</p>
        <p role="status">
          {{ t(persistent ? "preferences.local" : "preferences.memory") }}
        </p>
      </fieldset>
      <fieldset class="appearance-options">
        <legend>{{ t("appearance.title") }}</legend>
        <label v-for="value in ['dark', 'light'] as const" :key="value"
          ><input
            type="radio"
            name="appearance"
            :value="value"
            :checked="mode === value"
            @change="setMode(value)"
          />{{
            t(value === "dark" ? "appearance.dark" : "appearance.light")
          }}</label
        >
      </fieldset></template
    ></USlideover
  >
</template>
