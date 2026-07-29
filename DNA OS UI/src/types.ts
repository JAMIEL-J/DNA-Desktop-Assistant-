/**
 * AgentOS - Core Type Definitions
 */

export type AgentRole = 'Research' | 'Planner' | 'Developer' | 'Writer' | 'QA' | 'Analyst';

export type AgentStatus = 'Running' | 'Waiting' | 'Sleeping' | 'Paused' | 'Restarting' | 'Failed' | 'Crashed';

export type WindowTab = 
  | 'Terminal'
  | 'Timeline'
  | 'Memory'
  | 'Files'
  | 'Conversations'
  | 'Execution Graph'
  | 'Transparency'
  | 'Metrics';

export interface LogEntry {
  id: string;
  timestamp: string; // HH:MM:SS format
  message: string;
  level: 'info' | 'warn' | 'error' | 'success' | 'debug' | 'system';
  coloredPrefix?: string;
}

export interface TimelineStep {
  id: string;
  title: string;
  description: string;
  status: 'completed' | 'in_progress' | 'pending' | 'failed';
  timestamp: string;
  durationMs: number;
  outputPreview?: string;
}

export interface MemoryItem {
  id: string;
  key: string;
  value: string;
  type: 'vector_doc' | 'cache' | 'short_term' | 'long_term' | 'state';
  score?: number; // Similarity score for vectors (0-1)
  updatedAt: string;
  sizeBytes: number;
}

export interface ArtifactFile {
  id: string;
  path: string;
  language: string;
  content: string;
  diff?: string;
  sizeKb: number;
  lastModifiedBy: string;
  timestamp: string;
}

export interface GitCommitConversation {
  commitHash: string;
  parentHash?: string;
  author: string;
  agentRole: AgentRole;
  timestamp: string;
  executionId: string;
  summary: string;
  reasoningPrompt: string;
  reasoningExplanation: string;
  diffSummary: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  expanded?: boolean;
}

export interface DependencyNode {
  id: string;
  label: string;
  agentRole: AgentRole;
  status: 'idle' | 'active' | 'completed' | 'failed';
  upstreamIds: string[];
  downstreamIds: string[];
}

export interface TransparencyAudit {
  whatHappened: string;
  whyItHappened: string;
  inputPayload: string;
  outputResult: string;
  reasoningSummary: string[];
  dependencies: string[];
  confidenceScore: number; // 0-100
  executionDurationMs: number;
  modelUsed: string;
  tokensConsumed: number;
}

export interface AgentMetricsHistory {
  timestamps: string[];
  cpuUsage: number[];
  memoryUsage: number[];
  ioRate: number[];
  networkRate: number[];
}

export interface AgentProcess {
  id: string;
  pid: number;
  name: string;
  role: AgentRole;
  color: string; // Hex color code
  borderHex: string;
  status: AgentStatus;
  activeTask: string;
  runtimeSeconds: number;
  cpuUsagePercent: number;
  memoryUsageMb: number;
  activeTab: WindowTab;
  isMinimized: boolean;
  isMaximized: boolean;
  isFloating: boolean;
  isPinned: boolean;
  position?: { x: number; y: number; w: number; h: number }; // For floating windows
  
  // Tab Data
  logs: LogEntry[];
  timeline: TimelineStep[];
  memory: MemoryItem[];
  files: ArtifactFile[];
  conversations: GitCommitConversation[];
  dependencyNodes: DependencyNode[];
  transparency: TransparencyAudit;
  metricsHistory: AgentMetricsHistory;

  // Custom User Prompt / Gemini task running state
  customPrompt?: string;
  isCustomTaskRunning?: boolean;

  // Avatar & Visual Identity
  avatarUrl?: string;
  avatarTitle?: string;
  skillBadges?: string[];
}

export interface SystemTelemetry {
  cpuUsageTotal: number;
  cpuCores: number[];
  ramUsedGb: number;
  ramTotalGb: number;
  gpuUsagePercent: number;
  gpuTempC: number;
  networkRxKbps: number;
  networkTxKbps: number;
  diskUsagePercent: number;
  activeThreads: number;
  uptimeSeconds: number;
  history: {
    cpu: number[];
    ram: number[];
    gpu: number[];
    network: number[];
  };
}

export interface ProcessTreeNode {
  pid: number;
  ppid: number;
  name: string;
  user: string;
  cpuPercent: number;
  memMb: number;
  state: string;
  children?: ProcessTreeNode[];
}

export interface GlobalEvent {
  id: string;
  timestamp: string;
  sourceAgent: string;
  level: 'info' | 'warn' | 'error' | 'broadcast';
  message: string;
  executionId?: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
  read: boolean;
  agentRole?: AgentRole;
}

export interface ExecutionQueueTask {
  id: string;
  title: string;
  assignedAgentId: string;
  assignedAgentName: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'PAUSED';
  progressPercent: number;
  etaSeconds: number;
}

export type LayoutMode = '2x2_GRID' | '3_COLUMN' | 'SPLIT_MAIN' | 'FLOATING' | 'SINGLE_FOCUS';

export interface WorkspacePreset {
  id: string;
  name: string;
  description: string;
  layout: LayoutMode;
  agentIds: string[];
}
