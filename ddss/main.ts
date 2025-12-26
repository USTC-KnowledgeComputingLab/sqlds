import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { Command } from "commander";
import { main as ds } from "./ds.ts";
import { main as dump } from "./dump.ts";
import { main as egg } from "./egg.ts";
import { main as input } from "./input.ts";
import { main as load } from "./load.ts";
import { main as output } from "./output.ts";
import { initializeDatabase } from "./orm.ts";

const componentMap: Record<string, any> = {
    ds,
    egg,
    input,
    output,
    load,
    dump,
};

async function run(addr: string, components: string[]) {
    let sequelizeAddr = addr;
    if (addr.startsWith("sqlite:///")) {
        sequelizeAddr = `sqlite:${addr.replace("sqlite:///", "")}`;
    }

    const sequelize = await initializeDatabase(sequelizeAddr);

    try {
        const promises = components.map((name) => {
            const component = componentMap[name];
            if (!component) {
                console.error(`error: unsupported component: ${name}`);
                process.exit(1);
            }
            return component(addr, sequelize);
        });

        await Promise.all(promises);
    } finally {
        await sequelize.close();
    }
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
            if (!addr) {
                const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "ddss-"));
                const dbPath = path.join(tmpDir, "ddss.db");
                addr = `sqlite:///${dbPath}`;
            }

            console.log(`addr: ${addr}`);
            await run(addr, options.component);
        });

    program.parse();
}

if (import.meta.main) {
    cli();
}
