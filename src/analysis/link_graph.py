"""
Link graph builder using NetworkX.
Creates a directed graph from crawl data and computes graph metrics.
Includes overlap removal to ensure nodes never overlap.
"""
import logging
import math
import random

import networkx as nx

from src.config import NODE_SIZES
from src.gsc.models import LinkEdge, Page

logger = logging.getLogger(__name__)

# Minimum pixel distance between any two node centers.
# This is generous enough to guarantee visual separation even for
# the largest nodes (homepage radius ~50px after click bonus).
MIN_NODE_DISTANCE = 120.0


class LinkGraph:
    """
    Builds and analyzes a directed link graph from site data.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._pages: dict[str, Page] = {}
        self.skeleton_edges = set()

    def build_from_data(
        self,
        pages: dict[str, Page],
        edges: list[LinkEdge],
    ) -> nx.DiGraph:
        """
        Build a directed graph from pages and edges.

        Args:
            pages: Dict of URL -> Page
            edges: List of LinkEdge

        Returns:
            The built NetworkX DiGraph.
        """
        self.graph.clear()
        self._pages = pages

        # Add nodes
        for url, page in pages.items():
            self.graph.add_node(
                url,
                title=page.title,
                page_type=page.page_type,
                clicks=page.total_clicks,
                impressions=page.total_impressions,
                position=page.avg_position,
                ctr=page.avg_ctr,
                status_code=page.status_code,
            )

        # Add edges (deduplicated)
        seen_edges = set()
        for edge in edges:
            if edge.is_internal:
                key = (edge.source_url, edge.target_url)
                if key not in seen_edges:
                    seen_edges.add(key)
                    self.graph.add_edge(
                        edge.source_url,
                        edge.target_url,
                        anchor_text=edge.anchor_text,
                        shared_keywords=edge.shared_keywords,
                    )

        # Calculate BFS spanning tree for the skeleton
        roots = [n for n in self.graph.nodes if self.graph.nodes[n].get("page_type") == "homepage"]
        root = roots[0] if roots else (list(self.graph.nodes)[0] if self.graph.nodes else None)
        
        self.skeleton_edges = set()
        if root is not None:
            self.skeleton_edges = set(nx.bfs_edges(self.graph, root))
            visited = {root}.union({v for _, v in self.skeleton_edges})
            for node in self.graph.nodes:
                if node not in visited:
                    visited.add(node)
                    for u, v in nx.bfs_edges(self.graph, node):
                        self.skeleton_edges.add((u, v))
                        visited.add(v)
        
        # Tag edges objects with is_skeleton
        for edge in edges:
            if edge.is_internal:
                edge.is_skeleton = (edge.source_url, edge.target_url) in self.skeleton_edges

        logger.info(
            f"Graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges ({len(self.skeleton_edges)} skeleton)"
        )
        return self.graph

    def compute_pagerank(self) -> dict[str, float]:
        """Compute PageRank for all nodes."""
        try:
            return nx.pagerank(self.graph, alpha=0.85)
        except Exception as e:
            logger.error(f"PageRank computation failed: {e}")
            return {}

    # ── Node radius helper ────────────────────────────────────────────────

    def _node_radius(self, url: str) -> float:
        """Compute the visual radius that graph_view will use for *url*."""
        page = self._pages.get(url)
        if page is None:
            return 12.0
        base = NODE_SIZES.get(page.page_type, 12)
        bonus = min(math.log(page.total_clicks + 1) * 3, 20)
        return float(base + bonus)

    # ── Overlap removal ───────────────────────────────────────────────────

    def _remove_overlaps(
        self,
        pos: dict[str, tuple[float, float]],
        padding: float = 30.0,
        max_iterations: int = 200,
    ) -> dict[str, tuple[float, float]]:
        """
        Iteratively push overlapping nodes apart until every pair has
        at least ``r_i + r_j + padding`` pixels between their centres.

        Uses a simple repulsion‐only sweep that converges quickly for
        the typical site‐map sizes (< 500 nodes).
        """
        urls = list(pos.keys())
        n = len(urls)
        if n < 2:
            return pos

        # Mutable position arrays
        xs = {u: pos[u][0] for u in urls}
        ys = {u: pos[u][1] for u in urls}
        radii = {u: self._node_radius(u) for u in urls}

        for iteration in range(max_iterations):
            moved = False
            for i in range(n):
                for j in range(i + 1, n):
                    u, v = urls[i], urls[j]
                    dx = xs[v] - xs[u]
                    dy = ys[v] - ys[u]
                    dist = math.sqrt(dx * dx + dy * dy)
                    min_dist = radii[u] + radii[v] + padding

                    if dist < min_dist:
                        # Push apart along their connecting line
                        if dist < 0.01:
                            # Coincident → nudge in a random direction
                            angle = random.uniform(0, 2 * math.pi)
                            dx = math.cos(angle)
                            dy = math.sin(angle)
                            dist = 0.01

                        overlap = (min_dist - dist) / 2.0 + 1.0
                        nx_ = dx / dist
                        ny_ = dy / dist

                        xs[u] -= nx_ * overlap
                        ys[u] -= ny_ * overlap
                        xs[v] += nx_ * overlap
                        ys[v] += ny_ * overlap
                        moved = True

            if not moved:
                logger.info(
                    f"Overlap removal converged after {iteration + 1} iterations."
                )
                break
        else:
            logger.warning(
                f"Overlap removal did not fully converge after {max_iterations} iterations."
            )

        return {u: (xs[u], ys[u]) for u in urls}

    # ── Layout computation ────────────────────────────────────────────────

    def compute_layout(
        self,
        layout_type: str = "force",
        scale: float = 2400.0,
    ) -> dict[str, tuple[float, float]]:
        """
        Compute node positions using a graph layout algorithm, then run
        overlap removal so that every node has its own dedicated space.

        Args:
            layout_type: One of 'force', 'circular', 'tree', 'radial'.
            scale: Scaling factor for positions.

        Returns:
            Dict of URL -> (x, y) positions.
        """
        if self.graph.number_of_nodes() == 0:
            return {}

        n_nodes = self.graph.number_of_nodes()

        # Adaptive scale: more nodes → more room
        adaptive_scale = scale * max(1.0, math.sqrt(n_nodes / 20.0))

        try:
            if layout_type == "force":
                # Much larger k → stronger node repulsion
                k_val = max(
                    8.0 / math.sqrt(max(n_nodes, 1)),
                    3.0,
                )
                pos = nx.spring_layout(
                    self.graph,
                    k=k_val,
                    iterations=200,
                    scale=adaptive_scale,
                    seed=42,
                )
            elif layout_type == "smart_tree":
                # Only use skeleton (BFS tree) edges for force calculations to prevent hairballs
                skeleton_graph = nx.DiGraph()
                skeleton_graph.add_nodes_from(self.graph.nodes(data=True))
                # Add only skeleton edges
                skel_edges_list = [(u, v) for u, v, d in self.graph.edges(data=True) if (u,v) in self.skeleton_edges]
                skeleton_graph.add_edges_from(skel_edges_list)
                
                k_val = max(8.0 / math.sqrt(max(n_nodes, 1)), 4.0)
                pos = nx.spring_layout(
                    skeleton_graph,
                    k=k_val,
                    iterations=300,
                    scale=adaptive_scale,
                    seed=42,
                )
            elif layout_type == "circular":
                pos = nx.circular_layout(self.graph, scale=adaptive_scale)
            elif layout_type == "tree":
                roots = [
                    n for n in self.graph.nodes
                    if self.graph.nodes[n].get("page_type") == "homepage"
                ]
                root = roots[0] if roots else list(self.graph.nodes)[0]
                try:
                    pos = nx.bfs_layout(self.graph, root, scale=adaptive_scale)
                except Exception:
                    pos = nx.kamada_kawai_layout(
                        self.graph, scale=adaptive_scale
                    )
            elif layout_type == "radial":
                pos = nx.shell_layout(self.graph, scale=adaptive_scale)
            else:
                pos = nx.spring_layout(
                    self.graph, scale=adaptive_scale, seed=42
                )

            # Convert numpy arrays to plain floats
            pos = {
                url: (float(x), float(y)) for url, (x, y) in pos.items()
            }

            # ── Guarantee no overlaps ─────────────────────────────────
            pos = self._remove_overlaps(pos, padding=35.0)

            return pos

        except Exception as e:
            logger.error(f"Layout computation failed: {e}")
            return {}

    def get_node_metrics(self, url: str) -> dict:
        """Get computed metrics for a specific node."""
        if url not in self.graph:
            return {}

        return {
            "in_degree": self.graph.in_degree(url),
            "out_degree": self.graph.out_degree(url),
            "predecessors": list(self.graph.predecessors(url)),
            "successors": list(self.graph.successors(url)),
        }
