import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { Command } from "commander";
import type { Sequelize } from "sequelize";
import { main as ds } from "./ds.ts";
import { main as dump } from "./dump.ts";
import { main as egg } from "./egg.ts";
import { main as input } from "./input.ts";
import { main as load } from "./load.ts";
import { main as output } from "./output.ts";
import { initializeDatabase } from "./orm.ts";

type ComponentMain = (addr: string, sequelize: Sequelize) => Promise<void>;

const componentMap: Record<string, ComponentMain> = {
    ds,
    egg,
    input,
    output,
    load,
    dump,
};

async function run(addr: string, components: string[]) {
    for (const name of components) {
        if (!(name in componentMap)) {
            console.error(`error: unsupported component: ${name}`);
            return;
        }
    }

    const sequelize = await initializeDatabase(addr);

    const promises = components.map((name) => {
        const component = componentMap[name]!;
        return component(addr, sequelize);
    });

    await Promise.race(promises);

    await sequelize.close();
}

export function cli() {
    const program = new Command();

    program
        .name("ddss")
        .description("DDSS - Distributed Deductive System Sorts: Run DDSS with an interactive deductive environment.")
        .option("-a, --addr <url>", "Database address URL. If not provided, uses a temporary SQLite database.")
        .option("-c, --component <names...>", "Components to run.", ["input", "output", "ds", "egg"])
        .action(async (options) => {
            let addr = options.addr;
            let tmpDir: string | undefined;
            if (!addr) {
                tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "ddss-"));
                const dbPath = path.join(tmpDir, "ddss.db");
                addr = `sqlite:///${dbPath}`;
            }

            if (addr.startsWith("sqlite://")) {
                addr = addr.replace("sqlite:///", "sqlite:");
            } else if (addr.startsWith("mysql://")) {
                // Nothing to change
            } else if (addr.startsWith("mariadb://")) {
                // Nothing to change
            } else if (addr.startsWith("postgresql://")) {
                addr = addr.replace("postgresql://", "postgres://");
            } else {
                console.error(`error: unsupported database: ${addr}`);
                return;
            }

            console.log(`addr: ${addr}`);
            await run(addr, options.component);

            if (tmpDir) {
                await fs.rm(tmpDir, { recursive: true, force: true });
            }
        });

    program.parse();
}

if (import.meta.main) {
    cli();
}
