import json
from typing import List, Dict, Any

class DashboardGenerator:
    """
    Generates a standalone HTML dashboard for job search results.
    Uses Tailwind CSS for styling and provides a curated view of jobs based on LLM scores and tiers.
    """

    def generate(self, jobs: List[Dict[str, Any]]) -> str:
        """
        Produces a standalone HTML string from a list of enriched jobs.

        Args:
            jobs: List of job dictionaries containing 'title', 'company', 'link', 'tier',
                  'llm_score', 'llm_archetype', 'llm_insight', 'is_new', etc.

        Returns:
            A complete HTML page as a string.
        """
        if not jobs:
            return self._empty_state()

        # 1. Stats for Bento Header
        total_leads = len(jobs)
        strong_recommends = len([j for j in jobs if j.get('llm_score') in ['A', 'B', '4', '5'] or (isinstance(j.get('llm_score'), float) and j.get('llm_score') >= 4.0)])
        quick_apply = len([j for j in jobs if j.get('quick_apply', False)])

        # 2. The Gold Mine: Filter jobs with high LLM scores
        # Since the scorer might return 4.5 or 'A', we handle both.
        def is_gold(job):
            score = job.get('llm_score')
            if score is None: return False
            if isinstance(score, str):
                return score.upper() in ['A', 'B'] or (score.startswith('4') or score.startswith('5'))
            if isinstance(score, (int, float)):
                return score >= 4.0
            return False

        gold_mine_jobs = [j for j in jobs if is_gold(j)]
        general_jobs = [j for j in jobs if not is_gold(j)]

        # Sorting general jobs by tier: High > Medium > Low
        tier_priority = {"High": 0, "Medium": 1, "Low": 2}
        general_jobs.sort(key=lambda x: tier_priority.get(x.get('tier', 'Low'), 2))

        # HTML Template
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Job Search Intelligence Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Inter', sans-serif; background-color: #f8fafc; }}
                .gold-gradient {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); }}
                .tier-high {{ border-left: 4px solid #ef4444; }}
                .tier-medium {{ border-left: 4px solid #f59e0b; }}
                .tier-low {{ border-left: 4px solid #64748b; }}
            </style>
        </head>
        <body class="p-6 md:p-12">
            <div class="max-w-6xl mx-auto">
                <header class="mb-10">
                    <h1 class="text-4xl font-bold text-slate-900 tracking-tight">Job Intelligence <span class="text-blue-600">Dashboard</span></h1>
                    <p class="text-slate-500 mt-2">Curated leads and LLM-powered analysis for your career growth.</p>
                </header>

                <!-- Bento Header -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                        <p class="text-sm font-medium text-slate-500 uppercase tracking-wider">Total Leads</p>
                        <p class="text-3xl font-bold text-slate-900 mt-1">{total_leads}</p>
                    </div>
                    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 ring-2 ring-blue-500 ring-opacity-50">
                        <p class="text-sm font-medium text-blue-600 uppercase tracking-wider">Strong Recommends</p>
                        <p class="text-3xl font-bold text-slate-900 mt-1">{strong_recommends}</p>
                    </div>
                    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                        <p class="text-sm font-medium text-slate-500 uppercase tracking-wider">Quick-Apply Ready</p>
                        <p class="text-3xl font-bold text-slate-900 mt-1">{quick_apply}</p>
                    </div>
                </div>

                <!-- The Gold Mine -->
                <section class="mb-12">
                    <div class="flex items-center gap-2 mb-6">
                        <span class="text-2xl">✨</span>
                        <h2 class="text-2xl font-bold text-slate-800">The Gold Mine</h2>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {self._generate_gold_cards(gold_mine_jobs)}
                    </div>
                </section>

                <!-- General List -->
                <section>
                    <div class="flex items-center gap-2 mb-6">
                        <span class="text-2xl">📋</span>
                        <h2 class="text-2xl font-bold text-slate-800">All Other Leads</h2>
                    </div>
                    <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-slate-50 border-b border-slate-200">
                                <tr>
                                    <th class="px-6 py-4 text-sm font-semibold text-slate-600">Job Role</th>
                                    <th class="px-6 py-4 text-sm font-semibold text-slate-600">Company</th>
                                    <th class="px-6 py-4 text-sm font-semibold text-slate-600">Tier</th>
                                    <th class="px-6 py-4 text-sm font-semibold text-slate-600">Action</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100">
                                {self._generate_table_rows(general_jobs)}
                            </tbody>
                        </table>
                    </div>
                </section>
            </div>
        </body>
        </html>
        """
        return html

    def _generate_gold_cards(self, jobs: List[Dict[str, Any]]) -> str:
        if not jobs:
            return '<p class="text-slate-400 italic">No gold mine leads identified yet.</p>'

        cards = []
        for job in jobs:
            title = job.get('title', 'Unknown Role')
            company = job.get('company', 'Unknown Company')
            score = job.get('llm_score', 'N/A')
            archetype = job.get('llm_archetype', 'General')
            insight = job.get('llm_insight', 'No deep insight available.')
            link = job.get('link', '#')
            is_new = job.get('is_new', False)

            new_badge = '<span class="bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ml-2">New</span>' if is_new else ''

            cards.append(f"""
            <div class="gold-gradient p-6 rounded-2xl shadow-md border border-amber-200 flex flex-col h-full">
                <div class="flex justify-between items-start mb-4">
                    <div class="flex-1">
                        <h3 class="font-bold text-slate-900 leading-tight">{title}{new_badge}</h3>
                        <p class="text-sm text-amber-800 font-medium">{company}</p>
                    </div>
                    <div class="bg-white px-3 py-1 rounded-lg shadow-sm border border-amber-200">
                        <span class="text-xs font-bold text-amber-600 uppercase">Score:</span>
                        <span class="text-lg font-bold text-slate-900">{score}</span>
                    </div>
                </div>
                <div class="mb-4">
                    <span class="text-[10px] font-bold text-amber-700 uppercase tracking-widest block mb-1">Archetype</span>
                    <p class="text-sm font-semibold text-slate-800">{archetype}</p>
                </div>
                <div class="mb-6 flex-1">
                    <span class="text-[10px] font-bold text-amber-700 uppercase tracking-widest block mb-1">Strategic Insight</span>
                    <p class="text-sm text-slate-700 leading-relaxed italic">"{insight}"</p>
                </div>
                <a href="{link}" target="_blank" class="block text-center bg-slate-900 text-white text-sm font-bold py-2 rounded-xl hover:bg-slate-800 transition-colors">
                    Apply Now
                </a>
            </div>
            """)
        return "\\n".join(cards)

    def _generate_table_rows(self, jobs: List[Dict[str, Any]]) -> str:
        if not jobs:
            return '<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400 italic">No other leads found.</td></tr>'

        rows = []
        for job in jobs:
            title = job.get('title', 'Unknown Role')
            company = job.get('company', 'Unknown Company')
            tier = job.get('tier', 'Low')
            link = job.get('link', '#')
            is_new = job.get('is_new', False)

            new_badge = '<span class="bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ml-2">New</span>' if is_new else ''

            tier_class = f"tier-{tier.lower()}"
            tier_color = {
                "High": "text-red-600 bg-red-50",
                "Medium": "text-amber-600 bg-amber-50",
                "Low": "text-slate-600 bg-slate-50"
            }.get(tier, "text-slate-600 bg-slate-50")

            rows.append(f"""
            <tr class="{tier_class} hover:bg-slate-50 transition-colors">
                <td class="px-6 py-4">
                    <span class="font-medium text-slate-900">{title}</span>{new_badge}
                </td>
                <td class="px-6 py-4 text-sm text-slate-600">{company}</td>
                <td class="px-6 py-4">
                    <span class="px-2 py-1 rounded-md text-xs font-bold {tier_color}">{tier}</span>
                </td>
                <td class="px-6 py-4">
                    <a href="{link}" target="_blank" class="text-blue-600 hover:text-blue-800 text-sm font-semibold">View →</a>
                </td>
            </tr>
            """)
        return "\\n".join(rows)

    def _empty_state(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-50 flex items-center justify-center h-screen">
            <div class="text-center">
                <h1 class="text-2xl font-bold text-slate-800">No Jobs Found</h1>
                <p class="text-slate-500">Run a search to populate your dashboard.</p>
            </div>
        </body>
        </html>
        """
