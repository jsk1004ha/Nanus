import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const root = process.cwd();
const action = process.argv[2];
const isWindows = process.platform === "win32";

function systemPython() {
  return process.env.NANUS_PYTHON || "python";
}

function venvPython() {
  const candidates = isWindows
    ? [join(root, ".venv", "Scripts", "python.exe")]
    : [join(root, ".venv", "bin", "python")];
  return candidates.find((candidate) => existsSync(candidate)) || systemPython();
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    env: process.env,
    stdio: "inherit",
    shell: false,
    ...options,
  });
  if (result.error) {
    console.error(result.error.message);
  }
  process.exitCode = result.status ?? (result.error ? 1 : 0);
  if (process.exitCode !== 0) process.exit(process.exitCode);
}

if (action === "setup") {
  run(systemPython(), ["-m", "venv", ".venv"]);
  run(venvPython(), ["-m", "pip", "install", "-r", join("backend", "requirements.txt")]);
} else if (action === "dev") {
  run(venvPython(), [
    "-m",
    "uvicorn",
    "backend.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    process.env.NANUS_BACKEND_PORT || "8765",
    "--reload",
  ]);
} else if (action === "test" || action === "pytest") {
  run(venvPython(), ["-m", "pytest", "tests/backend", "-q"]);
} else {
  console.error("Usage: node scripts/backend.mjs <setup|dev|test|pytest>");
  process.exit(1);
}
