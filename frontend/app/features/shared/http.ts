import { es } from "../../i18n/es";
export function errorMessage(error: unknown): string {
  if (error instanceof TypeError) return es["assets.error"];
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object" && "detail" in error) {
    const detail = error.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((entry) =>
          typeof entry?.msg === "string" ? entry.msg : es["assets.invalid"],
        )
        .join(" · ");
    }
  }
  return es["assets.error"];
}

export function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.data === undefined) throw new Error(errorMessage(result.error));
  return result.data;
}

export async function allPages<T>(
  fetchPage: (offset: number) => Promise<T[]>,
): Promise<T[]> {
  const rows: T[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await fetchPage(offset);
    rows.push(...page);
    if (page.length < 100) return rows;
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
