import type { Sequelize } from "sequelize";
import { unparse } from "atsds-bnf";
import { Fact, Idea, initializeDatabase } from "./orm.ts";

export async function main(addr: string, sequelize?: Sequelize) {
    if (!sequelize) {
        sequelize = await initializeDatabase(addr);
    }

    const ideas = await Idea.findAll();
    for (const idea of ideas) {
        console.log("idea:", unparse(idea.data));
    }

    const facts = await Fact.findAll();
    for (const fact of facts) {
        console.log("fact:", unparse(fact.data));
    }
}
