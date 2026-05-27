import json
from typing import List, Dict, Any

class DashboardGenerator:
    """
    Generates a high-end, premium responsive HTML dashboard for job search results.
    Uses Tailwind CSS, Lucide Icons, and Marked.js to create a state-of-the-art
    experience with interactive tabs, live filters, and markdown rendering.
    """

    def generate(self, jobs: List[Dict[str, Any]]) -> str:
        """
        Produces a standalone HTML string from a list of enriched jobs.

        Args:
            jobs: List of job dictionaries.

        Returns:
            A complete HTML page as a string.
        """
        # Serialize jobs to JSON
        jobs_json = json.dumps(jobs, default=str)

        html = f"""<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Job Search Intelligence</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <!-- Marked.js for markdown parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        display: ['"Space Grotesk"', 'sans-serif'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            background-color: #0b0f19;
            color: #f1f5f9;
        }}
        .mesh-gradient {{
            background-image: 
                radial-gradient(at 10% 20%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 90% 10%, rgba(245, 158, 11, 0.08) 0px, transparent 50%),
                radial-gradient(at 50% 80%, rgba(16, 185, 129, 0.06) 0px, transparent 50%);
        }}
        .glass-panel {{
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .glass-card-gold {{
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.07) 0%, rgba(245, 158, 11, 0.03) 100%);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(245, 158, 11, 0.25);
        }}
        .glass-card-gold:hover {{
            border-color: rgba(245, 158, 11, 0.5);
            box-shadow: 0 0 25px rgba(245, 158, 11, 0.15);
        }}
        .glass-card-normal {{
            background: rgba(17, 24, 39, 0.5);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .glass-card-normal:hover {{
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 0 25px rgba(99, 102, 241, 0.08);
        }}
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0f172a;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #334155;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #475569;
        }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            color: #ffffff;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        .markdown-body h1 {{ font-size: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.25rem; }}
        .markdown-body h2 {{ font-size: 1.25rem; }}
        .markdown-body h3 {{ font-size: 1.1rem; }}
        .markdown-body p {{ margin-bottom: 1rem; color: #cbd5e1; line-height: 1.6; }}
        .markdown-body ul {{ list-style-type: disc; margin-left: 1.5rem; margin-bottom: 1rem; color: #cbd5e1; }}
        .markdown-body li {{ margin-bottom: 0.25rem; }}
        .markdown-body table {{ width: 100%; border-collapse: collapse; margin-bottom: 1rem; }}
        .markdown-body th {{ background: rgba(255,255,255,0.05); text-align: left; padding: 0.5rem; font-weight: 600; border: 1px solid rgba(255,255,255,0.1); }}
        .markdown-body td {{ padding: 0.5rem; border: 1px solid rgba(255,255,255,0.1); color: #cbd5e1; }}
        .markdown-body blockquote {{ border-left: 4px solid #f59e0b; padding-left: 1rem; margin-bottom: 1rem; italic: true; color: #94a3b8; }}
        .markdown-body code {{ background: rgba(255,255,255,0.08); padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.9em; }}
    </style>
</head>
<body class="h-full font-sans antialiased mesh-gradient overflow-x-hidden">
    <div class="min-h-screen flex flex-col">
        <!-- Navigation Header -->
        <nav class="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex items-center justify-between h-16">
                    <div class="flex items-center gap-3">
                        <div class="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-amber-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <i data-lucide="dna" class="h-5 w-5 text-white"></i>
                        </div>
                        <div>
                            <span class="font-display font-bold text-xl tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">DNA Job Intelligence</span>
                            <span class="text-[9px] uppercase tracking-widest font-semibold ml-2 px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Agent Mode</span>
                        </div>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
                            <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            Live Scanner Active
                        </div>
                    </div>
                </div>
            </div>
        </nav>

        <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <!-- Bento Dashboard Metrics -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div class="glass-panel p-5 rounded-2xl flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Leads Scanned</p>
                        <p id="stat-total-leads" class="text-3xl font-display font-bold text-white mt-1">0</p>
                    </div>
                    <div class="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                        <i data-lucide="layers" class="h-6 w-6"></i>
                    </div>
                </div>
                <div class="glass-panel p-5 rounded-2xl border-l-4 border-l-amber-500 flex items-center justify-between shadow-lg shadow-amber-500/5">
                    <div>
                        <p class="text-xs font-semibold text-amber-400 uppercase tracking-wider">The Gold Mine</p>
                        <p id="stat-gold-leads" class="text-3xl font-display font-bold text-white mt-1">0</p>
                    </div>
                    <div class="h-12 w-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                        <i data-lucide="sparkles" class="h-6 w-6"></i>
                    </div>
                </div>
                <div class="glass-panel p-5 rounded-2xl border-l-4 border-l-cyan-500 flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-cyan-400 uppercase tracking-wider">Fresh (24h)</p>
                        <p id="stat-new-leads" class="text-3xl font-display font-bold text-white mt-1">0</p>
                    </div>
                    <div class="h-12 w-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                        <i data-lucide="clock" class="h-6 w-6"></i>
                    </div>
                </div>
                <div class="glass-panel p-5 rounded-2xl flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Matched Roles</p>
                        <p id="stat-matched-roles" class="text-3xl font-display font-bold text-white mt-1">0</p>
                    </div>
                    <div class="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <i data-lucide="user-check" class="h-6 w-6"></i>
                    </div>
                </div>
            </div>

            <!-- Filters & Actions Toolbar -->
            <div class="glass-panel p-4 rounded-2xl mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div class="flex flex-1 flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                    <!-- Search Input -->
                    <div class="relative flex-1 max-w-md">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-400 pointer-events-none">
                            <i data-lucide="search" class="h-4 w-4"></i>
                        </span>
                        <input id="search-input" type="text" placeholder="Search by role, company, or archetype..." 
                               class="w-full bg-slate-900/50 border border-slate-700/50 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors">
                    </div>
                    <!-- Role Filter -->
                    <select id="role-filter" class="bg-slate-900/50 border border-slate-700/50 rounded-xl px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors">
                        <option value="all">All Roles</option>
                    </select>
                </div>

                <div class="flex items-center gap-3">
                    <span class="text-xs font-medium text-slate-400 uppercase tracking-wider">Sort by</span>
                    <select id="sort-select" class="bg-slate-900/50 border border-slate-700/50 rounded-xl px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors">
                        <option value="score-desc">Highest Score</option>
                        <option value="recency-desc">Newest First</option>
                        <option value="tier-desc">Tier Priority</option>
                    </select>
                </div>
            </div>

            <!-- Gold Mine Section -->
            <section class="mb-10">
                <div class="flex items-center justify-between mb-6">
                    <div class="flex items-center gap-2">
                        <div class="h-8 w-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                            <i data-lucide="sparkles" class="h-4 w-4"></i>
                        </div>
                        <h2 class="font-display font-bold text-2xl text-white">The Gold Mine</h2>
                    </div>
                    <span class="text-xs text-amber-400/80 bg-amber-500/5 border border-amber-500/10 px-2.5 py-1 rounded-full font-medium">Top Match Leads (Score &ge; 4.0)</span>
                </div>
                <div id="gold-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <!-- Cards will be dynamically inserted here -->
                </div>
            </section>

            <!-- All Other Leads Section -->
            <section>
                <div class="flex items-center gap-2 mb-6">
                    <div class="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                        <i data-lucide="list-filter" class="h-4 w-4"></i>
                    </div>
                    <h2 class="font-display font-bold text-2xl text-white">Standard & Discovery Leads</h2>
                </div>
                <div class="glass-panel rounded-2xl overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-slate-900/80 border-b border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-400">
                                    <th class="px-6 py-4">Job Role</th>
                                    <th class="px-6 py-4">Company</th>
                                    <th class="px-6 py-4">Tier Status</th>
                                    <th class="px-6 py-4">Match / Score</th>
                                    <th class="px-6 py-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="other-leads-tbody" class="divide-y divide-slate-800/60">
                                <!-- Table rows will be dynamically inserted here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        </main>

        <!-- Footer -->
        <footer class="border-t border-slate-800/80 bg-slate-950/40 py-6 mt-12">
            <div class="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500">
                DNA Desktop Natural Assistant &copy; 2026. Custom Redesigned Job Intelligence Platform.
            </div>
        </footer>
    </div>

    <!-- Side-Drawer Details Panel -->
    <div id="detail-drawer" class="fixed inset-0 z-50 overflow-hidden hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
        <div class="absolute inset-0 overflow-hidden">
            <!-- Background backdrop -->
            <div class="absolute inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity" onclick="closeDrawer()"></div>

            <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
                <div class="pointer-events-auto w-screen max-w-3xl transform transition-transform duration-300 ease-in-out glass-panel !bg-slate-900/95 border-l border-slate-800 flex flex-col h-full shadow-2xl">
                    <!-- Drawer Header -->
                    <div class="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
                        <div class="flex items-center gap-3">
                            <div id="drawer-score-badge" class="px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
                                <span class="block text-[10px] uppercase font-bold text-amber-500">Score</span>
                                <span id="drawer-score-value" class="text-xl font-bold text-white">4.3</span>
                            </div>
                            <div>
                                <h3 id="drawer-job-title" class="font-display font-bold text-xl text-white">Senior ML Engineer</h3>
                                <p id="drawer-company" class="text-sm text-slate-400 font-medium">Synthesia</p>
                            </div>
                        </div>
                        <button onclick="closeDrawer()" class="h-9 w-9 rounded-lg bg-slate-800/50 border border-slate-700/50 flex items-center justify-center text-slate-400 hover:text-white transition-colors">
                            <i data-lucide="x" class="h-5 w-5"></i>
                        </button>
                    </div>

                    <!-- Tabs Header -->
                    <div class="border-b border-slate-800 bg-slate-900/50 px-6">
                        <nav class="-mb-px flex space-x-6" aria-label="Tabs">
                            <button id="tab-overview-btn" onclick="switchTab('overview')" class="border-b-2 border-indigo-500 py-3 text-sm font-medium text-white">Analysis Overview</button>
                            <button id="tab-cv-btn" onclick="switchTab('cv')" class="border-b-2 border-transparent py-3 text-sm font-medium text-slate-400 hover:text-white hover:border-slate-700">CV Tailoring</button>
                            <button id="tab-prep-btn" onclick="switchTab('prep')" class="border-b-2 border-transparent py-3 text-sm font-medium text-slate-400 hover:text-white hover:border-slate-700">Interview Prep</button>
                            <button id="tab-raw-btn" onclick="switchTab('raw')" class="border-b-2 border-transparent py-3 text-sm font-medium text-slate-400 hover:text-white hover:border-slate-700">Full Raw Report</button>
                        </nav>
                    </div>

                    <!-- Drawer Content -->
                    <div class="flex-1 overflow-y-auto p-6 space-y-6">
                        <!-- Tab Content: Overview -->
                        <div id="tab-overview" class="tab-panel space-y-6">
                            <!-- Quick Info Cards -->
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div class="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl">
                                    <span class="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block mb-1">Detected Archetype</span>
                                    <p id="drawer-archetype" class="text-sm font-semibold text-slate-200">AI Platform (Evals) / Technical Data Analyst</p>
                                </div>
                                <div class="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl">
                                    <span class="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block mb-1">Posting Legitimacy</span>
                                    <p id="drawer-legitimacy" class="text-sm font-semibold text-slate-200">High Confidence</p>
                                </div>
                            </div>

                            <!-- Insight Section -->
                            <div class="bg-slate-950/20 border border-slate-800/40 rounded-xl p-5">
                                <h4 class="font-display font-semibold text-base text-white mb-3 flex items-center gap-2">
                                    <i data-lucide="compass" class="h-4 w-4 text-indigo-400"></i>
                                    Strategic Analysis & Insights
                                </h4>
                                <div id="drawer-insight-rendered" class="markdown-body text-sm text-slate-300">
                                    <!-- Dynamic Rendered Content -->
                                </div>
                            </div>
                        </div>

                        <!-- Tab Content: CV Tailoring -->
                        <div id="tab-cv" class="tab-panel space-y-6 hidden">
                            <div class="bg-slate-950/20 border border-slate-800/40 rounded-xl p-5">
                                <h4 class="font-display font-semibold text-base text-white mb-3 flex items-center gap-2">
                                    <i data-lucide="file-edit" class="h-4 w-4 text-amber-400"></i>
                                    Proposed CV Customizations
                                </h4>
                                <div id="drawer-cv-content" class="markdown-body text-sm text-slate-300">
                                    <!-- CV recommendations -->
                                </div>
                            </div>
                        </div>

                        <!-- Tab Content: Interview Prep -->
                        <div id="tab-prep" class="tab-panel space-y-6 hidden">
                            <div class="bg-slate-950/20 border border-slate-800/40 rounded-xl p-5">
                                <h4 class="font-display font-semibold text-base text-white mb-3 flex items-center gap-2">
                                    <i data-lucide="presentation" class="h-4 w-4 text-emerald-400"></i>
                                    Interview Strategy & STAR Scenarios
                                </h4>
                                <div id="drawer-prep-content" class="markdown-body text-sm text-slate-300">
                                    <!-- Interview plan -->
                                </div>
                            </div>
                        </div>

                        <!-- Tab Content: Full Raw Report -->
                        <div id="tab-raw" class="tab-panel space-y-6 hidden">
                            <div class="bg-slate-950/40 border border-slate-800/60 p-5 rounded-xl">
                                <div id="drawer-raw-report" class="markdown-body text-sm text-slate-300 whitespace-pre-wrap font-mono">
                                    <!-- Raw Markdown Output -->
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Drawer Footer -->
                    <div class="px-6 py-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
                        <span id="drawer-source-badge" class="text-xs text-slate-400">Source: Greenhouse</span>
                        <a id="drawer-apply-btn" href="#" target="_blank" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 text-white text-sm font-semibold hover:from-indigo-500 hover:to-indigo-600 transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/10">
                            Apply Now
                            <i data-lucide="external-link" class="h-4 w-4"></i>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Data Injection -->
    <script>
        const jobsData = {jobs_json};
        let currentDetailJob = null;

        // Initialize Lucide Icons
        window.addEventListener('DOMContentLoaded', () => {{
            initDashboard();
            lucide.createIcons();
        }});

        function initDashboard() {{
            // Populate stats
            document.getElementById('stat-total-leads').innerText = jobsData.length;
            
            const goldJobs = jobsData.filter(j => isGold(j));
            document.getElementById('stat-gold-leads').innerText = goldJobs.length;

            const newJobs = jobsData.filter(j => j.is_new);
            document.getElementById('stat-new-leads').innerText = newJobs.length;

            // Unique roles count
            const roles = new Set(jobsData.map(j => j.title.toLowerCase()));
            document.getElementById('stat-matched-roles').innerText = roles.size;

            // Populate role filter dropdown
            const roleSelect = document.getElementById('role-filter');
            const uniqueTitles = [...new Set(jobsData.map(j => j.title))].sort();
            uniqueTitles.forEach(title => {{
                const opt = document.createElement('option');
                opt.value = title;
                opt.innerText = title;
                roleSelect.appendChild(opt);
            }});

            // Bind events
            document.getElementById('search-input').addEventListener('input', render);
            document.getElementById('role-filter').addEventListener('change', render);
            document.getElementById('sort-select').addEventListener('change', render);

            // Initial render
            render();
        }}

        function isGold(job) {{
            const score = job.llm_score;
            if (score === null || score === undefined) return false;
            if (typeof score === 'string') {{
                const s = score.toUpperCase();
                return s === 'A' || s === 'B' || s.startsWith('4') || s.startsWith('5');
            }}
            if (typeof score === 'number') {{
                return score >= 4.0;
            }}
            return false;
        }}

        function getFilteredAndSortedJobs() {{
            const search = document.getElementById('search-input').value.toLowerCase();
            const roleFilter = document.getElementById('role-filter').value;
            const sortVal = document.getElementById('sort-select').value;

            let filtered = jobsData.filter(job => {{
                const matchSearch = (job.title || '').toLowerCase().includes(search) || 
                                    (job.company || '').toLowerCase().includes(search) || 
                                    (job.llm_archetype || '').toLowerCase().includes(search);
                const matchRole = roleFilter === 'all' || job.title === roleFilter;
                return matchSearch && matchRole;
            }});

            // Sorting
            const tierPriority = {{ "High": 0, "Medium": 1, "Low": 2 }};
            filtered.sort((a, b) => {{
                if (sortVal === 'score-desc') {{
                    const scoreA = parseFloat(a.llm_score) || 0;
                    const scoreB = parseFloat(b.llm_score) || 0;
                    return scoreB - scoreA;
                }} else if (sortVal === 'recency-desc') {{
                    const dateA = new Date(a.published || 0);
                    const dateB = new Date(b.published || 0);
                    return dateB - dateA;
                }} else if (sortVal === 'tier-desc') {{
                    const pA = tierPriority[a.tier] !== undefined ? tierPriority[a.tier] : 3;
                    const pB = tierPriority[b.tier] !== undefined ? tierPriority[b.tier] : 3;
                    return pA - pB;
                }}
                return 0;
            }});

            return filtered;
        }}

        function render() {{
            const filtered = getFilteredAndSortedJobs();
            
            // Separate Gold vs Other
            const goldJobs = filtered.filter(j => isGold(j));
            const otherJobs = filtered.filter(j => !isGold(j));

            renderGoldGrid(goldJobs);
            renderOtherTable(otherJobs);
        }}

        function renderGoldGrid(jobs) {{
            const grid = document.getElementById('gold-grid');
            grid.innerHTML = '';

            if (jobs.length === 0) {{
                grid.innerHTML = `
                    <div class="col-span-full py-8 text-center text-slate-500 italic">
                        No gold mine leads matched this filter.
                    </div>`;
                return;
            }}

            jobs.forEach(job => {{
                const newBadge = job.is_new ? '<span class="bg-indigo-500/20 text-indigo-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-indigo-500/20 ml-2">New</span>' : '';
                const score = job.llm_score || 'N/A';
                const card = document.createElement('div');
                card.className = "glass-card-gold p-6 rounded-2xl flex flex-col h-full transition-all duration-300 transform hover:-translate-y-1";
                card.innerHTML = `
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex-1">
                            <h3 class="font-display font-bold text-lg text-white leading-snug">${{job.title}}${{newBadge}}</h3>
                            <p class="text-sm text-amber-500/90 font-semibold mt-0.5">${{job.company}}</p>
                        </div>
                        <div class="bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/20 text-right">
                            <span class="text-[9px] font-bold text-amber-500 block uppercase leading-none">Score</span>
                            <span class="text-lg font-bold text-white leading-none">${{score}}</span>
                        </div>
                    </div>
                    <div class="mb-4 bg-slate-950/40 border border-slate-800/50 p-3 rounded-xl">
                        <span class="text-[9px] font-bold text-indigo-400 uppercase tracking-widest block mb-0.5">Archetype</span>
                        <p class="text-xs font-semibold text-slate-200">${{job.llm_archetype || 'N/A'}}</p>
                    </div>
                    <div class="mb-6 flex-1 text-xs text-slate-400 line-clamp-4 italic leading-relaxed">
                        ${{cleanInsightsSummary(job.llm_insight)}}
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <button onclick="openDrawer(${{jobsData.findIndex(j => j.link === job.link)}})" class="w-full text-center bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold py-2.5 rounded-xl transition-colors flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/15">
                            <i data-lucide="scan-face" class="h-4.5 w-4.5"></i>
                            View Analysis
                        </button>
                        <a href="${{job.link}}" target="_blank" class="w-full text-center bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold py-2.5 rounded-xl border border-slate-700/50 transition-colors flex items-center justify-center gap-1.5">
                            Apply
                            <i data-lucide="external-link" class="h-3.5 w-3.5"></i>
                        </a>
                    </div>
                `;
                grid.appendChild(card);
            }});
            lucide.createIcons();
        }}

        function stripReportNoise(text) {{
            if (!text || text === 'N/A') return '';
            let clean = text;
            // Strip loading/calling banners
            clean = clean.replace(/["']?📂[\s\S]*?══+[\s\S]*?══+\s*/g, '');
            clean = clean.replace(/🤖\s*Calling Gemini[^\n]*/g, '');
            clean = clean.replace(/📂\s*Loading context files[^\n]*/g, '');
            // Strip unicode box-drawing lines
            clean = clean.replace(/[═─]{6,}/g, '');
            // Strip SCORE_SUMMARY block
            clean = clean.replace(/---SCORE_SUMMARY---[\s\S]*?---END_SUMMARY---/g, '');
            // Strip report saved / tracker / emoji footer lines
            clean = clean.replace(/[✅📊]\s*(?:Report saved|Tracker entry)[^\n]*/g, '');
            clean = clean.replace(/Score:\s*[\d.]+\/5\s*\|[^\n]*/g, '');
            // Strip leading quotes and whitespace
            clean = clean.replace(/^["'\s]+/, '').replace(/["'\s]+$/, '');
            // Collapse excessive blank lines
            clean = clean.replace(/\n{3,}/g, '\n\n');
            return clean.trim();
        }}

        function cleanInsightsSummary(insightText) {{
            if (!insightText || insightText === 'N/A') return 'No strategic insight available.';
            let clean = stripReportNoise(insightText);
            // Try to find first meaningful paragraph (skip headers)
            const lines = clean.split('\n').filter(l => l.trim() && !l.startsWith('#') && !l.startsWith('|') && !l.startsWith('---') && !l.startsWith('*'));
            const summary = lines.slice(0, 3).join(' ').trim();
            return summary.length > 200 ? summary.substring(0, 200) + '…' : (summary || 'Detailed analysis available — click View Analysis.');
        }}

        function renderOtherTable(jobs) {{
            const tbody = document.getElementById('other-leads-tbody');
            tbody.innerHTML = '';

            if (jobs.length === 0) {{
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="px-6 py-8 text-center text-slate-500 italic">
                            No other matching leads.
                        </td>
                    </tr>`;
                return;
            }}

            jobs.forEach(job => {{
                const newBadge = job.is_new ? '<span class="bg-indigo-500/20 text-indigo-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-indigo-500/20 ml-2">New</span>' : '';
                const tierColor = {{
                    "High": "text-red-400 bg-red-500/10 border-red-500/20",
                    "Medium": "text-amber-400 bg-amber-500/10 border-amber-500/20",
                    "Low": "text-slate-400 bg-slate-800/50 border-slate-700/30"
                }}[job.tier] || "text-slate-400 bg-slate-800/50";

                const score = job.llm_score || 'Pending';
                
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-900/30 transition-colors";
                tr.innerHTML = `
                    <td class="px-6 py-4">
                        <span class="font-medium text-slate-200">${{job.title}}</span>${{newBadge}}
                    </td>
                    <td class="px-6 py-4 text-sm text-slate-400 font-medium">${{job.company}}</td>
                    <td class="px-6 py-4">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold border ${{tierColor}}">${{job.tier}}</span>
                    </td>
                    <td class="px-6 py-4 text-sm text-slate-300 font-semibold">${{score}}</td>
                    <td class="px-6 py-4 text-right">
                        <div class="flex items-center justify-end gap-2">
                            ${{job.llm_insight ? `
                            <button onclick="openDrawer(${{jobsData.findIndex(j => j.link === job.link)}})" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/50" title="View Analysis">
                                <i data-lucide="bar-chart-3" class="h-4 w-4"></i>
                            </button>` : ''}}
                            <a href="${{job.link}}" target="_blank" class="p-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white transition-colors border border-slate-700/50" title="Apply Externally">
                                <i data-lucide="external-link" class="h-4 w-4"></i>
                            </a>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            }});
            lucide.createIcons();
        }}

        // Side-drawer control
        function openDrawer(index) {{
            const job = jobsData[index];
            if (!job) return;

            currentDetailJob = job;

            // Fill header details
            document.getElementById('drawer-job-title').innerText = job.title;
            document.getElementById('drawer-company').innerText = job.company;
            document.getElementById('drawer-score-value').innerText = job.llm_score || 'N/A';
            document.getElementById('drawer-archetype').innerText = job.llm_archetype || 'Generalist';
            document.getElementById('drawer-legitimacy').innerText = job.llm_legitimacy || 'High Confidence';
            document.getElementById('drawer-source-badge').innerText = `Source: ${{job.source || 'Scraper'}} | Published: ${{job.published || 'N/A'}}`;
            document.getElementById('drawer-apply-btn').href = job.link;

            // Remove debug thinking banners from display
            let rawReportText = job.llm_insight || '';
            let cleanedReportText = stripReportNoise(rawReportText);

            // Segment report by headers if they exist to populate tabs
            const cvTabContent = extractSection(cleanedReportText, [/Bloque E/i, /Customization/i, /CV Tailoring/i]);
            const prepTabContent = extractSection(cleanedReportText, [/Bloque F/i, /Interview/i, /STAR/i]);
            const overviewContent = cleanedReportText
                .replace(/Bloque E[\s\S]*/i, '') // strip customization onward
                .replace(/Bloque F[\s\S]*/i, '');

            // Render Markdown
            document.getElementById('drawer-insight-rendered').innerHTML = marked.parse(overviewContent || 'No analysis preview available.');
            document.getElementById('drawer-cv-content').innerHTML = marked.parse(cvTabContent || 'No custom resume tailoring was needed for this role.');
            document.getElementById('drawer-prep-content').innerHTML = marked.parse(prepTabContent || 'No interview plan was generated.');
            document.getElementById('drawer-raw-report').innerText = cleanedReportText;

            // Switch to default tab
            switchTab('overview');

            // Show drawer
            const drawer = document.getElementById('detail-drawer');
            drawer.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            
            // Re-render icons inside drawer
            setTimeout(() => lucide.createIcons(), 50);
        }}

        function closeDrawer() {{
            const drawer = document.getElementById('detail-drawer');
            drawer.classList.add('hidden');
            document.body.style.overflow = '';
        }}

        function switchTab(tabName) {{
            // Hide all tab panels
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
            
            // Show target panel
            document.getElementById(`tab-${{tabName}}`).classList.remove('hidden');

            // Toggle active classes on tab buttons
            const tabs = ['overview', 'cv', 'prep', 'raw'];
            tabs.forEach(t => {{
                const btn = document.getElementById(`tab-${{t}}-btn`);
                if (t === tabName) {{
                    btn.className = "border-b-2 border-indigo-500 py-3 text-sm font-medium text-white";
                }} else {{
                    btn.className = "border-b-2 border-transparent py-3 text-sm font-medium text-slate-400 hover:text-white hover:border-slate-700";
                }}
            }});
        }}

        function extractSection(text, patterns) {{
            const lines = text.split('\n');
            let startIndex = -1;
            
            for (let i = 0; i < lines.length; i++) {{
                if (patterns.some(p => p.test(lines[i]))) {{
                    startIndex = i;
                    break;
                }}
            }}

            if (startIndex === -1) return '';

            // Extract until the next major header block or block section
            const resultLines = [];
            for (let i = startIndex; i < lines.length; i++) {{
                // Stop if we hit a different major block header
                if (i > startIndex && (/^##/i.test(lines[i]) || /Bloque [A-G]/i.test(lines[i]))) {{
                    break;
                }}
                resultLines.push(lines[i]);
            }}
            return resultLines.join('\n').trim();
        }}
    </script>
</body>
</html>
"""
        return html
