// Drizzle client. Uses DATABASE_URL from the environment.
//
// IMPORTANT: this connection should be configured to use the `hearme_web`
// Postgres role in production — that role has SELECT on everything but
// INSERT only on `questions` and `askers` (see db/init/02-roles.sql and
// ARCHITECTURE.md §4). Envelope/aggregate writes belong to the broker.

import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  // Throwing at import time during build would break `next build`, so we
  // only warn here. Server components that actually run a query will fail
  // loudly at request time, which is what we want.
  if (process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.warn(
      "[hearme-web] DATABASE_URL is not set; database queries will fail.",
    );
  }
}

// `prepare: false` avoids prepared-statement clashes when Next.js HMR
// recycles the module in dev.
const client = postgres(connectionString ?? "postgres://invalid", {
  prepare: false,
  max: 5,
});

export const db = drizzle(client, { schema });
export { schema };
