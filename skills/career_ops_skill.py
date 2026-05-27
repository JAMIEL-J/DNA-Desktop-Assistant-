"""
skills/career_ops_skill.py
Bridge skill for the Career-Ops AI Job Search Pipeline.
This skill wraps the Node.js based Career-Ops system, allowing DNA to use its
A-F scoring, ATS PDF generation, and portal scanning.
"""

import os
import subprocess
import logging
import re
from pathlib import Path
from typing import Any, Optional
import urllib.request
import html as html_lib

from config import (
    GOOGLE_API_KEY,
    CAREER_OPS_DIR,
    CAREER_OPS_NODE_PATH,
    CLOUD_LLM_MODEL,
)

logger = logging.getLogger('dna.skill.career_ops')

def _fetch_url_text(url: str) -> str:
    """Fetches a URL and returns cleaned text content suitable for LLM analysis."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='replace')
        
        # Strip script and style tags
        html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.IGNORECASE)
        # Convert structural tags to newlines
        html = re.sub(r'</?(?:p|div|br|h1|h2|h3|h4|h5|h6|li|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
        # Strip all HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode HTML entities
        text = html_lib.unescape(text)
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to fetch job description from URL {url}: {e}")
        return ""

def _run_node_script(script_name: str, args: list[str], env_vars: Optional[dict] = None) -> str:
    """Utility to run a Node.js script from the Career-Ops directory."""
    script_path = Path(CAREER_OPS_DIR) / script_name
    if not script_path.exists():
        logger.error("Career-Ops script not found: %s", script_path)
        return f"Error: Script {script_name} not found."

    # Prepare environment
    full_env = os.environ.copy()
    full_env["GEMINI_API_KEY"] = GOOGLE_API_KEY
    full_env["GEMINI_MODEL"] = CLOUD_LLM_MODEL
    if env_vars:
        full_env.update(env_vars)

    try:
        # We run from the CAREER_OPS_DIR so relative paths in the scripts work
        result = subprocess.run(
            [CAREER_OPS_NODE_PATH, str(script_path), *args],
            cwd=CAREER_OPS_DIR,
            capture_output=True,
            text=True,
            env=full_env,
            check=True,
            encoding='utf-8',
            errors='replace',
        )
        return result.stdout or ""
    except subprocess.CalledProcessError as e:
        logger.error("Node script %s failed: %s\nStdout: %s\nStderr: %s",
                     script_name, e, e.stdout, e.stderr)
        return f"Error executing {script_name}: {e.stderr or e.stdout or 'Unknown error'}"
    except Exception as e:
        logger.error("Unexpected error running %s: %s", script_name, e)
        return f"An unexpected error occurred: {str(e)}"

def career_ops_evaluate(jd_text: str) -> str:
    """
    Evaluate a job description using the Career-Ops A-F scoring matrix.
    Returns the full evaluation report and a summary of the score.
    """
    # If the input is a URL, fetch the actual text first
    if jd_text.strip().startswith(("http://", "https://")):
        url = jd_text.strip()
        logger.info(f"Fetching job description from URL: {url}")
        fetched_text = _fetch_url_text(url)
        if fetched_text:
            jd_text = f"Source URL: {url}\n\n{fetched_text}"
        else:
            logger.warning(f"Could not retrieve content from {url}, falling back to raw URL string.")

    # Use gemini-eval.mjs for the evaluation
    # we pass the JD text as a positional argument
    output = _run_node_script('gemini-eval.mjs', [jd_text])

    if "Error" in output:
        return output

    # Robust parsing of score, archetype, and legitimacy from the SCORE_SUMMARY block
    summary_match = re.search(
        r'---SCORE_SUMMARY---\s*COMPANY:\s*(.*?)\s*ROLE:\s*(.*?)\s*SCORE:\s*([\d\.]+)\s*ARCHETYPE:\s*(.*?)\s*LEGITIMACY:\s*(.*?)\s*---END_SUMMARY---',
        output,
        re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        company, role, score, archetype, legitimacy = summary_match.groups()
        # Clean the output to remove the summary block and any raw debug/loader lines
        clean_report = re.sub(r'---SCORE_SUMMARY---[\s\S]*?---END_SUMMARY---', '', output).strip()
        clean_report = re.sub(r'📂\s*Loading context files.*?(?:═{6,}[^\n]*\n){2}', '', clean_report, flags=re.DOTALL).strip()
        clean_report = re.sub(r'<think>[\s\S]*?</think>', '', clean_report).strip()
        
        return (f"Evaluation complete. Score: {score}/5. "
                f"Archetype: {archetype.strip()}. Legitimacy: {legitimacy.strip()}.\n\n"
                f"Full Report:\n{clean_report}")

    # Fallback to the old regex
    summary_match = re.search(r'Score: ([\d\.]+)/5\s*\|\s*Archetype: ([^|]+)\s*\|\s*Legitimacy: (.+)', output)
    if summary_match:
        score, archetype, legitimacy = summary_match.groups()
        clean_report = re.sub(r'📂\s*Loading context files.*?(?:═{6,}[^\n]*\n){2}', '', output, flags=re.DOTALL).strip()
        return (f"Evaluation complete. Score: {score}/5. "
                f"Archetype: {archetype.strip()}. Legitimacy: {legitimacy.strip()}.\n\n"
                f"Full Report:\n{clean_report}")

    return output

def career_ops_generate_pdf(input_html: str, output_pdf_name: str = "tailored_cv.pdf") -> str:
    """
    Generate an ATS-optimized PDF from an HTML template using Playwright.
    Input: Path to an HTML file (relative to Career-Ops dir or absolute).
    """
    output_path = Path(CAREER_OPS_DIR) / 'output' / output_pdf_name

    # Ensure output dir exists
    os.makedirs(output_path.parent, exist_ok=True)

    # node generate-pdf.mjs <input.html> <output.pdf>
    output = _run_node_script('generate-pdf.mjs', [input_html, str(output_path)])

    if "Error" in output:
        return output

    return f"Successfully generated tailored PDF: {output_path}\n\n{output}"

def career_ops_scan() -> str:
    """
    Scan configured job portals (Greenhouse, Ashby, Lever) for new offers.
    Updates pipeline.md and scan-history.tsv.
    """
    output = _run_node_script('scan.mjs', [])
    if "Error" in output:
        return output

    return f"Portal scan complete.\n\n{output}"

def career_ops_get_status(job_id: str) -> str:
    """
    Check the status of a specific job application from the tracker.
    """
    tracker_path = Path(CAREER_OPS_DIR) / 'data' / 'applications.md'
    if not tracker_path.exists():
        return "No application tracker found."

    content = tracker_path.read_text(encoding='utf-8')
    # Search for the job ID in the table
    # Example row: | 005 | 2026-05-13 | Google | AI Engineer | 4.2 | Applied | ...
    pattern = rf'\| {job_id} \|'
    match = re.search(pattern, content)

    if not match:
        return f"Could not find job ID {job_id} in the tracker."

    # Get the line containing the match
    line = [l for l in content.splitlines() if f'| {job_id} |' in l][0]
    columns = [c.strip() for c in line.split('|') if c.strip()]

    if len(columns) >= 5:
        return f"Job {job_id} ({columns[2]} - {columns[3]}) status: {columns[4]} (Score: {columns[3]})" # Note: indices might vary

    return f"Found job {job_id}, but could not parse status: {line}"

TOOLS = {
    "career_ops_evaluate": career_ops_evaluate,
    "career_ops_generate_pdf": career_ops_generate_pdf,
    "career_ops_scan": career_ops_scan,
    "career_ops_get_status": career_ops_get_status,
}
