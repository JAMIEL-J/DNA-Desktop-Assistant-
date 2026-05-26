# skills/memory_skill.py
# ──────────────────────────────────────────────────────────────────────
# Memory Skill
# Exposes tools for managing and querying the DNA semantic memory vault.
# ──────────────────────────────────────────────────────────────────────

import logging
from pathlib import Path
from pipeline.memory import get_semantic_context

logger = logging.getLogger('dna.skill.memory')

def sync_memory_vault() -> str:
    """Manually triggers the memory graph synchronization pipeline on the corpus."""
    try:
        logger.info("Starting memory vault graph synchronization...")
        from pipeline.graph_processor import GraphProcessor
        gp = GraphProcessor()
        gp.update_graph()
        return "Memory graph synchronization completed successfully, sir."
    except Exception as e:
        logger.error("Failed to sync memory vault: %s", e, exc_info=True)
        return f"Could not sync the memory vault: {str(e)}"

def query_memory_vault(entity: str) -> str:
    """Queries the semantic memory vault for relationships connected to a specific entity/concept."""
    try:
        logger.info("Querying memory vault for entity: %s", entity)
        triplets = get_semantic_context(entity)
        if not triplets:
            return f"I found no context or connections for '{entity}' in my memory, sir."
        
        # Translate technical graphify relations to human-like verbal phrases
        relation_mappings = {
            "conceptually_related_to": "is closely linked with",
            "semantically_similar_to": "is associated with",
            "references": "refers to",
            "expert_in": "specializes in",
            "relates_to": "is connected to",
        }
        
        response_lines = [f"Regarding '{entity}', sir, my memory shows the following connections:"]
        for t in triplets:
            src = t.get("source_label", t.get("source", ""))
            rel_key = t.get("relation", "relates_to").strip().lower().replace(" ", "_")
            tgt = t.get("target_label", t.get("target", ""))
            
            rel_phrase = relation_mappings.get(rel_key, rel_key.replace("_", " "))
            
            # Format as a clean, capitalized sentence with a period
            sentence = f"{src} {rel_phrase} {tgt}."
            if sentence:
                sentence = sentence[0].upper() + sentence[1:]
            response_lines.append(f"- {sentence}")
            
        return "\n".join(response_lines)
    except Exception as e:
        logger.error("Failed to query memory vault for '%s': %s", entity, e, exc_info=True)
        return f"I encountered an issue retrieving the memory context: {str(e)}"

def memorize_fact(category: str, fact: str) -> str:
    """Stores a specific fact or detail under a category in the persistent memory markdown file (Obsidian vault compatible), then updates the graph."""
    try:
        logger.info("Memorizing fact under category '%s': %s", category, fact)
        
        memory_file = Path("data/memory/corpus/persistent_memory.md")
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        category_title = category.strip().title()
        fact_clean = fact.strip()
        
        content = ""
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                content = f.read()
                
        if not content.strip():
            content = "# DNA Persistent Memory\n\n"
            
        category_header = f"## {category_title}"
        
        if category_header in content:
            # Locate section and insert fact
            parts = content.split(category_header)
            before = parts[0]
            after = parts[1]
            
            # Split off other sections following this one
            subparts = after.split("\n## ")
            section_body = subparts[0]
            rest = "\n## " + "\n## ".join(subparts[1:]) if len(subparts) > 1 else ""
            
            # Append if not a duplicate
            if fact_clean not in section_body:
                if not section_body.endswith("\n"):
                    section_body += "\n"
                section_body += f"- {fact_clean}\n"
                
            content = before + category_header + section_body + rest
        else:
            # Create new section
            if not content.endswith("\n\n"):
                if content.endswith("\n"):
                    content += "\n"
                else:
                    content += "\n\n"
            content += f"{category_header}\n- {fact_clean}\n"
            
        with open(memory_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Re-sync memory graph synchronously so it takes effect immediately
        from pipeline.graph_processor import GraphProcessor
        gp = GraphProcessor()
        gp.update_graph()
        
        return f"Saved the fact to '{category_title}' in persistent memory and updated the graph, sir."
    except Exception as e:
        logger.error("Failed to memorize fact: %s", e, exc_info=True)
        return f"I had trouble saving that detail to my persistent memory: {str(e)}"

TOOLS = {
    'sync_memory_vault': sync_memory_vault,
    'query_memory_vault': query_memory_vault,
    'memorize_fact': memorize_fact,
}
