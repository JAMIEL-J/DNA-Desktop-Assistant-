import os
import json
import logging
from pathlib import Path
import networkx as nx

logger = logging.getLogger('dna.graph_processor')

class GraphProcessor:
    def __init__(self, corpus_dir="data/memory/corpus", output_dir="graphify-out"):
        self.corpus_dir = Path(corpus_dir)
        self.output_dir = Path(output_dir)
        self.graph_path = self.output_dir / "graph.json"

    def update_graph(self) -> None:
        """
        Runs the graphify pipeline (detect -> extract -> build -> cluster -> to_json)
        on the files in the corpus directory, saving the output graph JSON.
        """
        try:
            self.corpus_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)

            from graphify.detect import detect
            detection = detect(self.corpus_dir)
            files_by_type = detection.get("files", {})

            code_files = [Path(p) for p in files_by_type.get("code", [])]
            doc_files = [Path(p) for p in files_by_type.get("document", [])]
            paper_files = [Path(p) for p in files_by_type.get("paper", [])]
            image_files = [Path(p) for p in files_by_type.get("image", [])]
            semantic_files = doc_files + paper_files + image_files

            # Extract AST from code files if any
            ast_result = {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}
            if code_files:
                from graphify.extract import extract as ast_extract
                try:
                    ast_result = ast_extract(code_files, cache_root=self.corpus_dir)
                except Exception as e:
                    logger.error("AST extraction failed: %s", e)

            # Extract semantic info from documents/images/papers if any
            sem_result = {"nodes": [], "edges": [], "hyperedges": [], "input_tokens": 0, "output_tokens": 0}
            if semantic_files:
                from graphify.llm import extract_corpus_parallel, detect_backend
                from graphify.cache import check_semantic_cache, save_semantic_cache
                
                backend = os.environ.get("GRAPHIFY_BACKEND")
                if not backend:
                    try:
                        backend = detect_backend()
                    except Exception:
                        pass
                if not backend:
                    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                        backend = "gemini"
                    elif os.environ.get("ANTHROPIC_API_KEY"):
                        backend = "claude"
                    else:
                        backend = "ollama"

                try:
                    sem_paths_str = [str(p) for p in semantic_files]
                    cached_nodes, cached_edges, cached_hyperedges, uncached_paths = check_semantic_cache(
                        sem_paths_str, root=self.corpus_dir
                    )
                    
                    sem_result["nodes"].extend(cached_nodes)
                    sem_result["edges"].extend(cached_edges)
                    sem_result["hyperedges"].extend(cached_hyperedges)

                    if uncached_paths:
                        fresh = extract_corpus_parallel(
                            [Path(p) for p in uncached_paths],
                            backend=backend,
                            root=self.corpus_dir
                        )
                        try:
                            save_semantic_cache(
                                fresh.get("nodes", []),
                                fresh.get("edges", []),
                                fresh.get("hyperedges", []),
                                root=self.corpus_dir
                            )
                        except Exception as exc:
                            logger.warning("Failed to save semantic cache: %s", exc)

                        sem_result["nodes"].extend(fresh.get("nodes", []))
                        sem_result["edges"].extend(fresh.get("edges", []))
                        sem_result["hyperedges"].extend(fresh.get("hyperedges", []))
                        sem_result["input_tokens"] += fresh.get("input_tokens", 0)
                        sem_result["output_tokens"] += fresh.get("output_tokens", 0)
                except Exception as e:
                    logger.error("Semantic extraction failed: %s", e)

            # Combine all nodes and edges
            merged = {
                "nodes": list(ast_result.get("nodes", [])) + list(sem_result.get("nodes", [])),
                "edges": list(ast_result.get("edges", [])) + list(sem_result.get("edges", [])),
                "hyperedges": list(sem_result.get("hyperedges", [])),
                "input_tokens": ast_result.get("input_tokens", 0) + sem_result.get("input_tokens", 0),
                "output_tokens": ast_result.get("output_tokens", 0) + sem_result.get("output_tokens", 0),
            }

            if not merged["nodes"]:
                # Empty graph case: write basic JSON to avoid failure
                with open(self.graph_path, "w", encoding="utf-8") as f:
                    json.dump({"nodes": [], "links": [], "hyperedges": []}, f)
                return

            from graphify.build import build
            from graphify.cluster import cluster
            from graphify.export import to_json

            # Build NetworkX graph
            G = build([merged], dedup=True, root=self.corpus_dir)
            communities = cluster(G)

            # Export graph and community structure to JSON
            to_json(G, communities, str(self.graph_path), force=True)
            logger.info("Successfully updated semantic graph at %s", self.graph_path)

        except Exception as e:
            logger.error("Failed to update graph: %s", e)
            # Create an empty file/structure on error to avoid breaking downstream
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                with open(self.graph_path, "w", encoding="utf-8") as f:
                    json.dump({"nodes": [], "links": [], "hyperedges": []}, f)
            except Exception:
                pass

    def load_graph(self) -> nx.Graph:
        """Loads and returns the NetworkX graph from the saved JSON output."""
        if not self.graph_path.exists():
            return nx.Graph()
        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            from graphify.build import build_from_json
            return build_from_json(data, directed=True, root=self.corpus_dir)
        except Exception as e:
            logger.error("Error loading graph from JSON: %s", e)
            return nx.Graph()

    def get_subgraph(self, entity: str) -> list[dict]:
        """
        Retrieves a list of connected triplets (edges/relationships) connected
        to any nodes matching the query entity (by ID or label).
        """
        G = self.load_graph()
        if not G or G.number_of_nodes() == 0:
            return []

        entity_norm = entity.strip().lower()
        matching_nodes = []
        for node_id, data in G.nodes(data=True):
            label = data.get("label", "").lower()
            if entity_norm in node_id.lower() or entity_norm in label:
                matching_nodes.append(node_id)

        if not matching_nodes:
            return []

        subgraph_edges = []
        seen_edges = set()
        for u, v, d in G.edges(data=True):
            if u in matching_nodes or v in matching_nodes:
                edge_key = (u, v, d.get("relation", ""))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    src_label = G.nodes[u].get("label", u)
                    tgt_label = G.nodes[v].get("label", v)
                    subgraph_edges.append({
                        "source": u,
                        "source_label": src_label,
                        "relation": d.get("relation", "relates_to"),
                        "target": v,
                        "target_label": tgt_label,
                        "confidence": d.get("confidence", "EXTRACTED")
                    })

        return subgraph_edges
