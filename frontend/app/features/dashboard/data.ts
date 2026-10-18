import { productionApi, type Schema } from "../production/api";
import { quickQuoteApi } from "../quick-quotes/api";
import { machinesApi } from "../machines/api";
import type { BlockId } from "./blocks";
import { productionStates } from "../../i18n/production";
import { quoteStatusLabels } from "../../i18n/quick-quotes";
export type DashboardRow = {
  id: string;
  title: string;
  to: string;
  status: string;
  updated: string;
  amount?: string;
};
export function taskRow(row: Schema["ProductionTaskRead"]): DashboardRow {
  return {
    id: row.id,
    title: `${row.code} · ${row.title}`,
    to: `/production/tasks/${row.id}`,
    status: productionStates[row.status],
    updated: row.updated_at,
  };
}
export function quoteRow(row: Schema["QuoteRead"]): DashboardRow {
  return {
    id: row.id,
    title: `${row.code} · ${row.title}`,
    to: `/quotes/${row.id}`,
    status: quoteStatusLabels[row.status],
    updated: row.updated_at,
    amount: `${row.currency} ${row.breakdown.final_price}`,
  };
}
export function latest(rows: DashboardRow[]) {
  return [...rows].sort((a, b) => b.updated.localeCompare(a.updated));
}
export function dashboardApi(base: string) {
  const production = productionApi(base),
    quotes = quickQuoteApi(base),
    machines = machinesApi(base);
  return {
    async load(id: BlockId): Promise<DashboardRow[]> {
      if (id === "production")
        return (await production.tasks())
          .filter((row) =>
            ["queued", "in_progress", "paused"].includes(row.status),
          )
          .map(taskRow);
      if (id === "quotes")
        return (await quotes.quotes())
          .filter((row) => row.status === "draft")
          .map(quoteRow);
      if (id === "machines")
        return (await machines.list()).map((row) => ({
          id: row.id,
          title: row.name,
          to: `/machines/${row.id}`,
          status: row.active ? "Activa" : "Inactiva",
          updated: row.updated_at,
        }));
      const [tasks, offers] = await Promise.all([
        production.tasks(),
        quotes.quotes(),
      ]);
      if (id === "attention")
        return [
          ...tasks.filter((row) => row.status === "paused").map(taskRow),
          ...offers.filter((row) => row.status === "expired").map(quoteRow),
        ];
      return latest([...tasks.map(taskRow), ...offers.map(quoteRow)]);
    },
  };
}
