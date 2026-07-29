import React, { useState } from 'react';
import { Database, Search, HardDrive, Cpu, Filter, ShieldCheck } from 'lucide-react';
import { AgentProcess, MemoryItem } from '../../types';

interface MemoryTabProps {
  agent: AgentProcess;
}

export const MemoryTab: React.FC<MemoryTabProps> = ({ agent }) => {
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');

  const filteredItems = agent.memory.filter((item) => {
    const matchesSearch =
      item.key.toLowerCase().includes(searchFilter.toLowerCase()) ||
      item.value.toLowerCase().includes(searchFilter.toLowerCase());
    const matchesType = selectedType === 'all' || item.type === selectedType;
    return matchesSearch && matchesType;
  });

  const getTypeBadge = (type: MemoryItem['type']) => {
    switch (type) {
      case 'vector_doc':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/30">VECTOR_DOC</span>;
      case 'cache':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">CACHE_HIT</span>;
      case 'state':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/30">STATE_VAR</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-400">{type.toUpperCase()}</span>;
    }
  };

  const totalBytes = agent.memory.reduce((acc, m) => acc + m.sizeBytes, 0);

  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* Memory Header & Controls */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <span className="font-semibold text-zinc-200">Milvus / Redis Vector & State Memory</span>
          </div>
          <span className="text-[11px] text-zinc-500">
            Total Allocated: {(totalBytes / 1024).toFixed(1)} KB ({agent.memory.length} keys)
          </span>
        </div>

        {/* Search & Filter bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 flex items-center bg-[#050507] border border-zinc-800 px-2.5 py-1 rounded">
            <Search className="w-3.5 h-3.5 text-zinc-500 mr-2" />
            <input
              type="text"
              placeholder="Search vector embeddings, keys, values..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="bg-transparent text-zinc-100 placeholder-zinc-600 focus:outline-none w-full text-xs"
            />
          </div>

          <div className="flex items-center gap-1 bg-[#050507] border border-zinc-800 rounded px-2 py-1 text-[11px]">
            <Filter className="w-3 h-3 text-zinc-500" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-transparent text-zinc-300 focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-zinc-900">All Types</option>
              <option value="vector_doc" className="bg-zinc-900">Vector Embeddings</option>
              <option value="cache" className="bg-zinc-900">Cache Hits</option>
              <option value="state" className="bg-zinc-900">State Variables</option>
              <option value="short_term" className="bg-zinc-900">Short-Term</option>
            </select>
          </div>
        </div>
      </div>

      {/* Memory Items List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-[#07070a]">
        {filteredItems.length > 0 ? (
          filteredItems.map((item) => (
            <div key={item.id} className="p-3 bg-[#0b0b0e] border border-zinc-900 rounded space-y-1.5 hover:border-zinc-800 transition">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getTypeBadge(item.type)}
                  <span className="font-bold text-zinc-200 text-xs">{item.key}</span>
                </div>
                {item.score !== undefined && (
                  <span className="text-[10px] text-emerald-400 font-bold bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/30">
                    Similarity: {(item.score * 100).toFixed(1)}%
                  </span>
                )}
              </div>

              <div className="p-2 bg-[#030305] rounded border border-zinc-900 text-zinc-300 font-mono text-[11px] whitespace-pre-wrap break-all">
                {item.value}
              </div>

              <div className="flex items-center justify-between text-[10px] text-zinc-500 pt-1">
                <span>Updated: {item.updatedAt}</span>
                <span>Size: {item.sizeBytes} bytes</span>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center text-zinc-600 py-12">No memory items match current filter query</div>
        )}
      </div>
    </div>
  );
};
