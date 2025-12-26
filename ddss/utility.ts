import { format } from "node:util";
import type { Interface } from "node:readline";
import { stdout } from "node:process";

export function strRuleGetStrIdea(data: string): string | null {
    if (!data.startsWith("--")) {
        const lines = data.split("\n");
        return `----\n${lines[0]}\n`;
    }
    return null;
}

export function patchStdout(rl: Interface) {
    const originalWrite = stdout.write;
    const originalLog = console.log;
    const originalError = console.error;
    let isReprompting = false;

    // @ts-ignore
    stdout.write = (chunk: string, encoding?: any, callback?: any) => {
        // (1) Use original write when reprompting to avoid infinite recursion
        // since rl.prompt() internally calls stdout.write.
        if (isReprompting) {
            return originalWrite.call(stdout, chunk, encoding, callback);
        }

        // (2) Let normal newlines (e.g., from user pressing Enter) pass through
        // without triggering the reprompting logic.
        if (chunk === "\n" || chunk === "\r\n") {
            return originalWrite.call(stdout, chunk, encoding, callback);
        }

        if (chunk.includes("\n")) {
            // Move cursor to the start of the line.
            originalWrite.call(stdout, "\r");

            const result = originalWrite.call(stdout, chunk, encoding, callback);

            isReprompting = true;
            rl.prompt();
            isReprompting = false;

            return result;
        }

        return originalWrite.call(stdout, chunk, encoding, callback);
    };

    console.log = (...args: any[]) => {
        stdout.write(format(...args) + "\n");
    };
    console.error = (...args: any[]) => {
        stdout.write(format(...args) + "\n");
    };

    return () => {
        // @ts-ignore
        stdout.write = originalWrite;
        console.log = originalLog;
        console.error = originalError;
    };
}
