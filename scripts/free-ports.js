// Kills whatever is currently listening on the backend (8000) and frontend (5173) dev ports
// before a fresh `npm run dev` starts. Runs automatically as the "predev" script.
//
// Why this exists: repeatedly stopping/restarting the dev servers (e.g. across many Claude
// Code sessions) can leave orphaned uvicorn/vite processes still bound to these ports. A new
// launch then either fails to bind :8000, or Vite silently moves to :5174+ — which breaks
// every API call, since the backend's CORS is pinned to exactly http://localhost:5173.
const { execSync } = require("child_process");

const PORTS = [8000, 5173];

for (const port of PORTS) {
  let output;
  try {
    // No "-p TCP" filter here — on this system it silently excludes IPv6-bound listeners
    // (Vite listens on [::1]:5173), which caused this script to miss the frontend process
    // entirely. Plain `netstat -ano` includes both IPv4 and IPv6 TCP listeners; the regex
    // below already anchors on the literal "TCP" protocol column to skip UDP rows.
    output = execSync(`netstat -ano`, { encoding: "utf8" });
  } catch {
    continue;
  }

  const pids = new Set();
  for (const line of output.split("\n")) {
    const match = line.match(/^\s*TCP\s+\S*:(\d+)\s+\S+\s+LISTENING\s+(\d+)/);
    if (match && Number(match[1]) === port) {
      pids.add(match[2]);
    }
  }

  for (const pid of pids) {
    try {
      execSync(`taskkill /PID ${pid} /F`, { stdio: "ignore" });
      console.log(`[free-ports] Killed stale process ${pid} on port ${port}`);
    } catch {
      // Already gone, or couldn't be killed — either way, move on.
    }
  }
}
