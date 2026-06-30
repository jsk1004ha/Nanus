import { spawn } from "node:child_process";

const isWindows = process.platform === "win32";
const npm = isWindows ? "npm.cmd" : "npm";
const node = process.execPath;

const children = new Set();

function start(command, args, env = {}) {
  const child = spawn(command, args, {
    cwd: process.cwd(),
    env: { ...process.env, ...env },
    stdio: "inherit",
    shell: false,
  });
  children.add(child);
  child.on("exit", (code, signal) => {
    children.delete(child);
    if (signal) return;
    if (code && code !== 0) {
      shutdown(code);
    }
  });
  return child;
}

function shutdown(code = 0) {
  for (const child of children) {
    if (!child.killed) child.kill();
  }
  process.exit(code);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

start(node, ["scripts/backend.mjs", "dev"]);
start(npm, ["run", "dev"], {
  VITE_NANUS_BACKEND_AUTO: "true",
  VITE_NANUS_RESTORE_BACKEND: "true",
});
