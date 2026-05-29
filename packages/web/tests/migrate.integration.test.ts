// End-to-end check that scripts/migrate.mjs upgrades a "staging-shaped" DB
// (volume that already has 0000_init.sql applied) without losing data and is
// idempotent on re-run.
//
// Strategy: spin up postgres:16 via `docker run`, apply the BASELINE
// 0000_init.sql by hand (simulating what initdb did when the staging volume
// was first created), insert one yes/no question, then invoke the migrator
// twice and assert the new column / CHECK constraint / preserved row /
// `_schema_migrations` ledger.
//
// Skipped if `docker` is not available (e.g. CI without Docker-in-Docker).
// Single test, ~60s budget.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { execSync, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import postgres from "postgres";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..", "..");
const BASELINE_SQL = join(REPO_ROOT, "packages/web/drizzle/0000_init.sql");
const MIGRATE_SCRIPT = join(REPO_ROOT, "packages/web/scripts/migrate.mjs");

function dockerAvailable(): boolean {
  const r = spawnSync("docker", ["info"], { stdio: "ignore" });
  return r.status === 0;
}

function pickFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer();
    srv.listen(0, () => {
      const addr = srv.address();
      if (typeof addr === "object" && addr) {
        const port = addr.port;
        srv.close(() => resolve(port));
      } else {
        srv.close(() => reject(new Error("no port")));
      }
    });
    srv.on("error", reject);
  });
}

async function waitFor(fn: () => Promise<boolean>, timeoutMs = 30000): Promise<void> {
  const start = Date.now();
  let lastErr: unknown = null;
  while (Date.now() - start < timeoutMs) {
    try {
      if (await fn()) return;
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`timed out after ${timeoutMs}ms: ${lastErr}`);
}

const skipSuite = !dockerAvailable();

(skipSuite ? describe.skip : describe)(
  "migrate.mjs against a real Postgres",
  () => {
    let containerName = "";
    let dsn = "";

    beforeAll(async () => {
      const port = await pickFreePort();
      containerName = `hearme-migtest-${process.pid}-${Date.now()}`;
      execSync(
        `docker run -d --rm --name ${containerName} ` +
          `-e POSTGRES_PASSWORD=t -e POSTGRES_DB=hearme ` +
          `-p ${port}:5432 postgres:16`,
        { stdio: "ignore" },
      );
      dsn = `postgres://postgres:t@127.0.0.1:${port}/hearme`;

      // Wait until Postgres is accepting connections.
      const probe = postgres(dsn, { max: 1, onnotice: () => {} });
      try {
        await waitFor(async () => {
          try {
            await probe`SELECT 1`;
            return true;
          } catch {
            return false;
          }
        });
      } finally {
        await probe.end({ timeout: 5 });
      }

      // Bootstrap the BASELINE schema (what initdb would have applied on
      // the first boot of an existing staging volume).
      const baseline = readFileSync(BASELINE_SQL, "utf8");
      const sql = postgres(dsn, { max: 1, onnotice: () => {} });
      try {
        await sql.unsafe(baseline);
        // One pre-existing yes/no question — proves the ALTER preserves rows.
        await sql`INSERT INTO askers(id, display_name) VALUES (gen_random_uuid(), 'baseline')`;
        await sql`
          INSERT INTO questions(text, closes_at)
          VALUES ('Pre-existing yes/no question?', now() + interval '1 day')
        `;
      } finally {
        await sql.end({ timeout: 5 });
      }
    }, 60_000);

    afterAll(() => {
      if (containerName) {
        spawnSync("docker", ["rm", "-f", containerName], { stdio: "ignore" });
      }
    });

    function runMigrator(): { status: number; stdout: string; stderr: string } {
      const r = spawnSync("node", [MIGRATE_SCRIPT], {
        env: { ...process.env, MIGRATOR_DATABASE_URL: dsn },
        encoding: "utf8",
      });
      return {
        status: r.status ?? -1,
        stdout: r.stdout ?? "",
        stderr: r.stderr ?? "",
      };
    }

    it("applies 0001 to a staging-shaped DB, preserves data, is idempotent", async () => {
      // Pre-migration: confirm the baseline really lacks the new column,
      // so the test would actually fail if the migrator didn't do its job.
      const probe = postgres(dsn, { max: 1, onnotice: () => {} });
      try {
        const cols0 = await probe`
          SELECT column_name FROM information_schema.columns
          WHERE table_name = 'questions' AND column_name = 'options'
        `;
        expect(cols0).toHaveLength(0);
      } finally {
        await probe.end({ timeout: 5 });
      }

      // First migrator run: applies 0001.
      const first = runMigrator();
      expect(
        first.status,
        `first run failed:\n${first.stdout}\n${first.stderr}`,
      ).toBe(0);
      expect(first.stdout).toMatch(/baselining 0000_init/);
      expect(first.stdout).toMatch(/applying 0001_add_options/);

      // Verify the column, default, CHECK, and preserved row.
      const sql = postgres(dsn, { max: 1, onnotice: () => {} });
      try {
        const cols = await sql`
          SELECT column_name, data_type, column_default, is_nullable
          FROM information_schema.columns
          WHERE table_name = 'questions' AND column_name = 'options'
        `;
        expect(cols).toHaveLength(1);
        expect(cols[0].data_type).toBe("jsonb");
        expect(cols[0].is_nullable).toBe("NO");

        const [row] = await sql`
          SELECT options FROM questions WHERE text = 'Pre-existing yes/no question?'
        `;
        expect(row.options).toEqual(["yes", "no"]);

        // CHECK constraint: < 2 options rejected.
        await expect(
          sql`
            INSERT INTO questions(text, closes_at, options)
            VALUES ('bad', now() + interval '1 day', '["only"]'::jsonb)
          `,
        ).rejects.toThrow(/questions_options_chk/);

        // CHECK constraint: > 8 options rejected.
        await expect(
          sql`
            INSERT INTO questions(text, closes_at, options)
            VALUES (
              'bad', now() + interval '1 day',
              '["a","b","c","d","e","f","g","h","i"]'::jsonb
            )
          `,
        ).rejects.toThrow(/questions_options_chk/);

        // 3-option insert succeeds.
        await sql`
          INSERT INTO questions(text, closes_at, options)
          VALUES (
            'three-option', now() + interval '1 day',
            '["red","blue","green"]'::jsonb
          )
        `;

        // Ledger: both versions recorded.
        const versions = await sql`
          SELECT version FROM _schema_migrations ORDER BY version
        `;
        expect(versions.map((r) => r.version)).toEqual([
          "0000_init",
          "0001_add_options",
        ]);
      } finally {
        await sql.end({ timeout: 5 });
      }

      // Second run: no-op. No new versions recorded, no errors.
      const second = runMigrator();
      expect(
        second.status,
        `second run failed:\n${second.stdout}\n${second.stderr}`,
      ).toBe(0);
      expect(second.stdout).not.toMatch(/applying /);
      expect(second.stdout).toMatch(/done \(0 applied/);

      const sql2 = postgres(dsn, { max: 1, onnotice: () => {} });
      try {
        const [{ count }] = await sql2`
          SELECT COUNT(*)::int AS count FROM _schema_migrations
        `;
        expect(count).toBe(2);
      } finally {
        await sql2.end({ timeout: 5 });
      }
    }, 60_000);
  },
);
