export const blockIds = [
  "production",
  "quotes",
  "attention",
  "activity",
  "machines",
] as const;
export type BlockId = (typeof blockIds)[number];
