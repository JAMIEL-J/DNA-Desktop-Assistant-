import { ProcessTreeNode, SystemTelemetry } from '../types';

export const generateInitialTelemetry = (): SystemTelemetry => ({
  cpuUsageTotal: 34.2,
  cpuCores: [28.4, 45.1, 19.8, 62.0, 14.5, 38.2, 51.0, 22.4],
  ramUsedGb: 14.8,
  ramTotalGb: 32.0,
  gpuUsagePercent: 54.0,
  gpuTempC: 62.5,
  networkRxKbps: 4120,
  networkTxKbps: 1840,
  diskUsagePercent: 42.1,
  activeThreads: 148,
  uptimeSeconds: 84920,
  history: {
    cpu: [22, 28, 35, 41, 38, 29, 34, 42, 39, 34],
    ram: [45, 45, 46, 46, 47, 47, 48, 48, 48, 48],
    gpu: [30, 42, 60, 58, 52, 65, 54, 58, 54, 52],
    network: [12, 18, 45, 80, 62, 54, 38, 42, 41, 39],
  },
});

export const getUpdatedTelemetry = (prev: SystemTelemetry): SystemTelemetry => {
  const nextCpuCores = prev.cpuCores.map((c) => {
    const jitter = (Math.random() - 0.48) * 8;
    return Math.min(99, Math.max(4, Math.round((c + jitter) * 10) / 10));
  });

  const nextCpuTotal = Math.round(
    (nextCpuCores.reduce((a, b) => a + b, 0) / nextCpuCores.length) * 10
  ) / 10;

  const ramJitter = (Math.random() - 0.48) * 0.1;
  const nextRam = Math.min(31.5, Math.max(8.0, Math.round((prev.ramUsedGb + ramJitter) * 10) / 10));

  const gpuJitter = (Math.random() - 0.48) * 6;
  const nextGpu = Math.min(98, Math.max(10, Math.round((prev.gpuUsagePercent + gpuJitter) * 10) / 10));

  const rxJitter = (Math.random() - 0.45) * 400;
  const txJitter = (Math.random() - 0.45) * 200;
  const nextRx = Math.max(100, Math.round(prev.networkRxKbps + rxJitter));
  const nextTx = Math.max(80, Math.round(prev.networkTxKbps + txJitter));

  const updateHistory = (arr: number[], newVal: number) => [...arr.slice(1), newVal];

  return {
    ...prev,
    cpuUsageTotal: nextCpuTotal,
    cpuCores: nextCpuCores,
    ramUsedGb: nextRam,
    gpuUsagePercent: nextGpu,
    gpuTempC: Math.round((58 + nextGpu * 0.15) * 10) / 10,
    networkRxKbps: nextRx,
    networkTxKbps: nextTx,
    uptimeSeconds: prev.uptimeSeconds + 1,
    history: {
      cpu: updateHistory(prev.history.cpu, nextCpuTotal),
      ram: updateHistory(prev.history.ram, Math.round((nextRam / prev.ramTotalGb) * 100)),
      gpu: updateHistory(prev.history.gpu, nextGpu),
      network: updateHistory(prev.history.network, Math.min(100, Math.round(nextRx / 100))),
    },
  };
};

export const generateProcessTree = (): ProcessTreeNode[] => [
  {
    pid: 1,
    ppid: 0,
    name: 'agentos-init',
    user: 'root',
    cpuPercent: 0.1,
    memMb: 18.2,
    state: 'S',
    children: [
      {
        pid: 8000,
        ppid: 1,
        name: 'agentd (Kernel Daemon)',
        user: 'system',
        cpuPercent: 2.4,
        memMb: 142.0,
        state: 'S',
        children: [
          { pid: 8042, ppid: 8000, name: 'Atlas-Research [vector-search]', user: 'agent_res', cpuPercent: 18.4, memMb: 412.0, state: 'R' },
          { pid: 8043, ppid: 8000, name: 'Chronos-Planner [dag-scheduler]', user: 'agent_plan', cpuPercent: 12.1, memMb: 328.0, state: 'R' },
          { pid: 8044, ppid: 8000, name: 'Nexus-Developer [cargo-build]', user: 'agent_dev', cpuPercent: 64.8, memMb: 840.0, state: 'R' },
          { pid: 8045, ppid: 8000, name: 'Vigil-QA [chaos-mesh]', user: 'agent_qa', cpuPercent: 42.5, memMb: 290.0, state: 'R' },
          { pid: 8046, ppid: 8000, name: 'Scribe-Writer [ast-parser]', user: 'agent_wri', cpuPercent: 2.4, memMb: 195.0, state: 'S' },
          { pid: 8047, ppid: 8000, name: 'Prism-Analyst [metrics-engine]', user: 'agent_ana', cpuPercent: 28.6, memMb: 512.0, state: 'R' },
        ],
      },
      {
        pid: 9012,
        ppid: 1,
        name: 'milvus-standalone',
        user: 'milvus',
        cpuPercent: 8.2,
        memMb: 1048.0,
        state: 'S',
      },
    ],
  },
];

/**
 * Renders an inline SVG Sparkline graph
 */
export const renderSparklineSvg = (data: number[], color: string = '#3b82f6', width: number = 70, height: number = 18) => {
  if (!data || data.length === 0) return null;

  const min = Math.min(...data, 0);
  const max = Math.max(...data, 100);
  const range = max - min || 1;

  const points = data
    .map((val, idx) => {
      const x = (idx / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" class="overflow-visible">
      <polyline
        fill="none"
        stroke="${color}"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        points="${points}"
      />
    </svg>
  `;
};
