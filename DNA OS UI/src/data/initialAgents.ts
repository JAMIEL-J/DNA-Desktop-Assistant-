import { AgentProcess, AgentRole } from '../types';

export const ROLE_COLORS: Record<AgentRole, { bg: string; text: string; border: string; hex: string }> = {
  Research: { bg: 'bg-purple-950/40', text: 'text-purple-400', border: 'border-purple-500/40', hex: '#a855f7' },
  Planner: { bg: 'bg-orange-950/40', text: 'text-orange-400', border: 'border-orange-500/40', hex: '#f97316' },
  Developer: { bg: 'bg-cyan-950/40', text: 'text-cyan-400', border: 'border-cyan-500/40', hex: '#06b6d4' },
  Writer: { bg: 'bg-emerald-950/40', text: 'text-emerald-400', border: 'border-emerald-500/40', hex: '#22c55e' },
  QA: { bg: 'bg-blue-950/40', text: 'text-blue-400', border: 'border-blue-500/40', hex: '#3b82f6' },
  Analyst: { bg: 'bg-red-950/40', text: 'text-red-400', border: 'border-red-500/40', hex: '#ef4444' },
};

export const INITIAL_AGENTS: AgentProcess[] = [
  {
    id: 'agent-nexus-01',
    pid: 9001,
    name: 'JARVIS',
    role: 'Planner',
    color: 'text-purple-400',
    borderHex: '#a855f7',
    status: 'Waiting',
    activeTask: 'Awaiting user command / Standby mode',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.1,
    memoryUsageMb: 120,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: true,
    logs: [
      { id: 'log-n-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'JARVIS Orchestrator online. Connected to Blackboard & Gemini API.', level: 'system' },
      { id: 'log-n-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'API Status: READY (Google Gemini 3.5 Flash Lite). Awaiting user directive...', level: 'info' }
    ],
    timeline: [],
    memory: [
      { id: 'mem-n-1', key: 'active_orchestrator', value: 'JARVIS', type: 'state', updatedAt: 'READY', sizeBytes: 128 },
    ],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'Initialized system connection.',
      whyItHappened: 'System boot sequence.',
      inputPayload: 'NONE',
      outputResult: 'READY',
      reasoningSummary: ['API key verified', 'Connected to Blackboard'],
      dependencies: ['OpenRouter API', 'Blackboard'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'gemini-3.5-flash-lite',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.1],
      memoryUsage: [120],
      ioRate: [0],
      networkRate: [0]
    }
  },
  {
    id: 'agent-cipher-02',
    pid: 9002,
    name: 'CIPHER',
    role: 'Analyst',
    color: 'text-cyan-400',
    borderHex: '#06b6d4',
    status: 'Waiting',
    activeTask: 'Data & Job Scraper Engine Ready',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.1,
    memoryUsageMb: 140,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: true,
    logs: [
      { id: 'log-c-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'CIPHER Data Engine online. Apify SDK & Excel exporter ready.', level: 'system' },
      { id: 'log-c-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'API Status: READY (Google Gemini 3.5 Flash Lite). Awaiting user directive...', level: 'info' }
    ],
    timeline: [],
    memory: [],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'Engine initialized.',
      whyItHappened: 'Boot check.',
      inputPayload: 'NONE',
      outputResult: 'READY',
      reasoningSummary: ['Apify token loaded', 'Pandas & OpenPyXL verified'],
      dependencies: ['Apify SDK', 'pandas'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'gemini-3.5-flash-lite',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.1],
      memoryUsage: [140],
      ioRate: [0],
      networkRate: [0]
    }
  },
  {
    id: 'agent-forge-03',
    pid: 9003,
    name: 'FORGE',
    role: 'Developer',
    color: 'text-orange-400',
    borderHex: '#f97316',
    status: 'Waiting',
    activeTask: 'ATS Resume AST Matcher Ready',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.1,
    memoryUsageMb: 110,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: false,
    logs: [
      { id: 'log-f-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'FORGE Career Agent online. Persistent profile loaded.', level: 'system' },
      { id: 'log-f-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Status: IDLE / Awaiting task directive...', level: 'info' }
    ],
    timeline: [],
    memory: [],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'Profile connected.',
      whyItHappened: 'Boot check.',
      inputPayload: 'NONE',
      outputResult: 'READY',
      reasoningSummary: ['Candidate profile connected'],
      dependencies: ['persistent_memory.md'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'google/gemma-4-26b-a4b-it:free',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.1],
      memoryUsage: [110],
      ioRate: [0],
      networkRate: [0]
    }
  },
  {
    id: 'agent-argus-04',
    pid: 9004,
    name: 'ARGUS',
    role: 'QA',
    color: 'text-emerald-400',
    borderHex: '#22c55e',
    status: 'Waiting',
    activeTask: 'Desktop Screen & Window Monitor Active',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.2,
    memoryUsageMb: 95,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: false,
    logs: [
      { id: 'log-a-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'ARGUS Vision & Desktop monitor online. Watching window events.', level: 'system' },
      { id: 'log-a-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Status: READY.', level: 'info' }
    ],
    timeline: [],
    memory: [],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'Desktop vision active.',
      whyItHappened: 'System monitor thread.',
      inputPayload: 'NONE',
      outputResult: 'MONITORING',
      reasoningSummary: ['pywin32 hook active'],
      dependencies: ['pywin32'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'vision-local',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.2],
      memoryUsage: [95],
      ioRate: [0],
      networkRate: [0]
    }
  },
  {
    id: 'agent-hermes-05',
    pid: 9005,
    name: 'HERMES',
    role: 'Research',
    color: 'text-blue-400',
    borderHex: '#3b82f6',
    status: 'Waiting',
    activeTask: 'Web Crawler & Search Specialist Ready',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.1,
    memoryUsageMb: 105,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: false,
    logs: [
      { id: 'log-h-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'HERMES Web Engine online. HTTP/HTTPS client ready.', level: 'system' },
      { id: 'log-h-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Status: IDLE / Ready to fetch web resources.', level: 'info' }
    ],
    timeline: [],
    memory: [],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'HTTP stack initialized.',
      whyItHappened: 'Boot sequence.',
      inputPayload: 'NONE',
      outputResult: 'READY',
      reasoningSummary: ['Network interface verified'],
      dependencies: ['urllib3'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'gemini-2.5-flash',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.1],
      memoryUsage: [105],
      ioRate: [0],
      networkRate: [0]
    }
  },
  {
    id: 'agent-titan-06',
    pid: 9006,
    name: 'TITAN',
    role: 'Writer',
    color: 'text-red-400',
    borderHex: '#ef4444',
    status: 'Waiting',
    activeTask: 'System Resource & Quotas Daemon Active',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.1,
    memoryUsageMb: 85,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: false,
    logs: [
      { id: 'log-t-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'TITAN System Daemon online. RAM & CPU quotas verified.', level: 'system' },
      { id: 'log-t-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Status: READY / Standby.', level: 'info' }
    ],
    timeline: [],
    memory: [],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'Hardware quota checked.',
      whyItHappened: 'Boot check.',
      inputPayload: 'psutil',
      outputResult: 'OK',
      reasoningSummary: ['System resources within threshold'],
      dependencies: ['psutil'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'system-native',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.1],
      memoryUsage: [85],
      ioRate: [0],
      networkRate: [0]
    }
  },
  {
    id: 'agent-vanguard-07',
    pid: 9007,
    name: 'VANGUARD',
    role: 'Developer',
    color: 'text-teal-400',
    borderHex: '#2dd4b6',
    status: 'Waiting',
    activeTask: 'File & Storage Operator Ready',
    runtimeSeconds: 0,
    cpuUsagePercent: 0.1,
    memoryUsageMb: 90,
    activeTab: 'Terminal',
    isMinimized: false,
    isMaximized: false,
    isFloating: false,
    isPinned: false,
    logs: [
      { id: 'log-v-1', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'VANGUARD Storage agent online. File operations ready.', level: 'system' },
      { id: 'log-v-2', timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }), message: 'Status: READY / Standby.', level: 'info' }
    ],
    timeline: [],
    memory: [],
    files: [],
    conversations: [],
    dependencyNodes: [],
    transparency: {
      whatHappened: 'Storage agent initialized.',
      whyItHappened: 'Boot check.',
      inputPayload: 'NONE',
      outputResult: 'READY',
      reasoningSummary: ['Folder index ready'],
      dependencies: ['file_skill'],
      confidenceScore: 100.0,
      executionDurationMs: 0,
      modelUsed: 'system-native',
      tokensConsumed: 0
    },
    metricsHistory: {
      timestamps: ['00:00'],
      cpuUsage: [0.1],
      memoryUsage: [90],
      ioRate: [0],
      networkRate: [0]
    }
  }
];

export const INITIAL_PRESETS = [
  {
    id: 'preset-dna-swarm',
    name: 'Full 7-Agent DNA Swarm',
    description: '3-Column dense view showing active DNA Swarm specialists (JARVIS, CIPHER, FORGE, ARGUS, HERMES, TITAN, VANGUARD)',
    layout: '3_COLUMN' as const,
    agentIds: ['agent-nexus-01', 'agent-cipher-02', 'agent-forge-03', 'agent-argus-04', 'agent-hermes-05', 'agent-titan-06', 'agent-vanguard-07']
  }
];
