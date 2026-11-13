export const routes = [
  { path: "/overview", label: "Overview", heading: "Payments overview", description: "Your payment workspace" },
  { path: "/payables", label: "Payables", heading: "Supplier payment queue", description: "Review and manage requests" },
  { path: "/mandate", label: "Mandate", heading: "Payment limits and approvals", description: "Manage spending protections" },
  { path: "/setup", label: "Setup", heading: "XRPL Testnet wallet setup", description: "Configure your testnet workspace" },
] as const;

export type RoutePath = (typeof routes)[number]["path"];

export function normalizeRoute(hash: string): RoutePath {
  const path = hash.replace(/^#/, "").split("?")[0].replace(/\/$/, "") || "/overview";
  return routes.find((route) => route.path === path)?.path ?? "/overview";
}

export function filterRoutes(query: string) {
  const term = query.trim().toLocaleLowerCase();
  return routes.filter((route) =>
    (route.label + " " + route.description).toLocaleLowerCase().includes(term)
  );
}
