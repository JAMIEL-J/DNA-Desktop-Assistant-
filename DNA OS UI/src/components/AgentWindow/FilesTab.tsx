import React, { useState } from 'react';
import { FileCode, Folder, Copy, Check, FileText, Code2, Download } from 'lucide-react';
import { AgentProcess, ArtifactFile } from '../../types';

interface FilesTabProps {
  agent: AgentProcess;
}

export const FilesTab: React.FC<FilesTabProps> = ({ agent }) => {
  const [selectedFile, setSelectedFile] = useState<ArtifactFile | null>(agent.files[0] || null);
  const [viewMode, setViewMode] = useState<'code' | 'diff'>('code');
  const [copied, setCopied] = useState(false);

  const handleCopyCode = () => {
    if (!selectedFile) return;
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-[#050507] text-zinc-300 font-mono text-xs overflow-hidden">
      {/* File Header */}
      <div className="p-3 bg-[#0a0a0d] border-b border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-orange-400" />
          <span className="font-semibold text-zinc-200">Workspace Code Artifacts</span>
          <span className="text-[11px] text-zinc-500">({agent.files.length} artifacts)</span>
        </div>

        {selectedFile && (
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-[#050507] border border-zinc-800 rounded p-0.5 text-[10px]">
              <button
                onClick={() => setViewMode('code')}
                className={`px-2 py-0.5 rounded transition ${viewMode === 'code' ? 'bg-zinc-800 text-zinc-100 font-bold' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                Source Code
              </button>
              {selectedFile.diff && (
                <button
                  onClick={() => setViewMode('diff')}
                  className={`px-2 py-0.5 rounded transition ${viewMode === 'diff' ? 'bg-zinc-800 text-zinc-100 font-bold' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  Git Diff
                </button>
              )}
            </div>

            <button
              onClick={handleCopyCode}
              className="flex items-center gap-1 px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-[10px]"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Split: File Tree Explorer & Code Editor Panel */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 overflow-hidden divide-y md:divide-y-0 md:divide-x divide-zinc-900">
        {/* File Navigation List */}
        <div className="overflow-y-auto p-2 bg-[#07070a] space-y-1">
          <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-zinc-500 font-bold flex items-center gap-1">
            <Folder className="w-3 h-3 text-amber-400" /> /workspace/
          </div>
          {agent.files.map((file) => {
            const isSelected = selectedFile?.id === file.id;
            return (
              <button
                key={file.id}
                onClick={() => setSelectedFile(file)}
                className={`w-full text-left px-2.5 py-1.5 rounded transition flex items-center justify-between text-xs ${
                  isSelected
                    ? 'bg-orange-950/30 border border-orange-500/40 text-orange-200 font-medium'
                    : 'hover:bg-zinc-900/50 text-zinc-400'
                }`}
              >
                <div className="truncate flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                  <span className="truncate">{file.path}</span>
                </div>
                <span className="text-[10px] text-zinc-600 shrink-0">{file.sizeKb}KB</span>
              </button>
            );
          })}
        </div>

        {/* Code Content Display */}
        <div className="md:col-span-2 overflow-y-auto bg-[#030305] p-3">
          {selectedFile ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] border-b border-zinc-900 pb-2 text-zinc-400">
                <span className="font-bold text-zinc-200">{selectedFile.path}</span>
                <span>Language: {selectedFile.language.toUpperCase()} | Modified: {selectedFile.timestamp}</span>
              </div>

              {viewMode === 'code' ? (
                <pre className="p-3 bg-[#060608] border border-zinc-900/80 rounded font-mono text-xs text-zinc-200 leading-relaxed overflow-x-auto whitespace-pre">
                  {selectedFile.content}
                </pre>
              ) : (
                <pre className="p-3 bg-[#060608] border border-zinc-900/80 rounded font-mono text-xs text-emerald-400 leading-relaxed overflow-x-auto whitespace-pre">
                  {selectedFile.diff}
                </pre>
              )}
            </div>
          ) : (
            <div className="text-center text-zinc-600 py-12">No file selected to view</div>
          )}
        </div>
      </div>
    </div>
  );
};
