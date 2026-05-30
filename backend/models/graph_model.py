"""
backend/models/graph_model.py
------------------------------
Implements the road network as a weighted graph and Dijkstra's
shortest-path algorithm.

Key concepts:
  - Graph: adjacency list (dict of dicts) for O(1) edge lookup
  - Edge weight: distance_km * congestion_delay_multiplier
  - Dijkstra: min-heap (priority queue) for O((V+E)logV) time complexity
  - Dynamic rerouting: simply recalculate with updated weights

Why adjacency list (not matrix)?
  Road networks are SPARSE — a city with 1000 intersections has far fewer
  than 1000² roads. Adjacency list uses O(V+E) space; matrix uses O(V²).
"""

import heapq
from typing import Optional

# ─── Road type → base capacity ───────────────────────────────────────────────
ROAD_TYPE_MAP = {
    "R1": "highway",  "R2": "arterial", "R3": "local",
    "R4": "arterial", "R5": "highway",  "R6": "local",
    "R7": "arterial", "R8": "local",
}

# ─── Congestion → travel time multiplier ─────────────────────────────────────
CONGESTION_DELAY = {
    "Low":    1.0,
    "Medium": 2.2,
    "High":   5.0,
    None:     1.5,
}


class RoadNetwork:
    """
    Represents the city road network as an undirected weighted graph.

    Attributes:
        graph : dict[node -> dict[neighbor -> {distance, road_id, weight}]]
        congestion_state : dict[road_id -> congestion_level]
    """

    def __init__(self, edges: list, congestion_state: Optional[dict] = None):
        """
        Builds the adjacency-list graph from a list of edge definitions.

        edges format:
            [(node_a, node_b, distance_km, road_id), ...]

        congestion_state:
            {road_id: "Low"|"Medium"|"High"}
        """
        self.graph            = {}
        self.congestion_state = congestion_state or {}
        self.edges_raw        = edges          # Store for reset / re-weighting

        for edge in edges:
            self._add_edge(*edge)

    # ── Graph construction ────────────────────────────────────────────────────

    def _add_edge(self, a: str, b: str, dist: float, road_id: str):
        """Adds a bidirectional edge between a and b."""
        for node in (a, b):
            if node not in self.graph:
                self.graph[node] = {}

        weight = self._compute_weight(dist, road_id)

        self.graph[a][b] = {
            "distance": dist,
            "road_id":  road_id,
            "weight":   weight,
            "congestion": self.congestion_state.get(road_id),
        }
        self.graph[b][a] = {
            "distance": dist,
            "road_id":  road_id,
            "weight":   weight,
            "congestion": self.congestion_state.get(road_id),
        }

    def _compute_weight(self, distance: float, road_id: str) -> float:
        """
        Edge weight = distance_km × congestion_delay_multiplier

        This is the cost Dijkstra minimizes — it represents effective
        travel time rather than raw physical distance.

        Example:
          2 km road with High congestion → weight = 2 * 5.0 = 10.0
          2 km road with Low  congestion → weight = 2 * 1.0 = 2.0
          Dijkstra will strongly prefer the Low-congestion road.
        """
        cong  = self.congestion_state.get(road_id)
        delay = CONGESTION_DELAY.get(cong, 1.5)
        return round(distance * delay, 4)

    # ── Dynamic rerouting support ─────────────────────────────────────────────

    def update_congestion(self, road_id: str, new_level: str):
        """
        Updates congestion for a road and recomputes ALL affected edge weights.

        This simulates real-time traffic changes:
          - A traffic incident is reported on Road R4
          - We call update_congestion("R4", "High")
          - Graph weights for all edges using R4 change instantly
          - Next Dijkstra call will route around it automatically
        """
        self.congestion_state[road_id] = new_level

        # Rebuild adjacency list for all edges using this road_id
        for a, b, dist, rid in self.edges_raw:
            if rid == road_id:
                weight = self._compute_weight(dist, road_id)
                if a in self.graph and b in self.graph[a]:
                    self.graph[a][b]["weight"]    = weight
                    self.graph[a][b]["congestion"] = new_level
                if b in self.graph and a in self.graph[b]:
                    self.graph[b][a]["weight"]    = weight
                    self.graph[b][a]["congestion"] = new_level

    def update_all_congestion(self, congestion_dict: dict):
        """Bulk-updates congestion for all roads from a prediction dict."""
        for road_id, level in congestion_dict.items():
            self.update_congestion(road_id, level)

    # ── Dijkstra's Algorithm ──────────────────────────────────────────────────

    def dijkstra(self, source: str, target: str) -> dict:
        """
        Finds the minimum-weight path from source to target using Dijkstra's
        algorithm with a binary min-heap priority queue.

        Algorithm step-by-step:
          1. Initialize dist[source] = 0, all others = ∞
          2. Push (0, source) into the min-heap
          3. While heap is not empty:
             a. Pop node u with smallest tentative distance
             b. If u == target → found shortest path, stop early
             c. For each neighbor v of u:
                new_dist = dist[u] + weight(u, v)
                if new_dist < dist[v]:
                  dist[v] = new_dist
                  prev[v] = u
                  push (new_dist, v) to heap
          4. Reconstruct path from prev[] dict

        Time complexity:  O((V + E) log V)
        Space complexity: O(V)

        Where V = number of intersections, E = number of roads.

        Returns dict with:
          path         : list of node names from source to target
          total_weight : total effective travel cost (distance × delay)
          total_distance_km : physical distance (no congestion penalty)
          edges_used   : list of (from, to, road_id, congestion, weight)
          found        : bool — whether a path exists
        """
        if source not in self.graph:
            return {"found": False, "error": f"Source node '{source}' not in graph"}
        if target not in self.graph:
            return {"found": False, "error": f"Target node '{target}' not in graph"}

        # ── Initialise ────────────────────────────────────────────────────────
        INF      = float("inf")
        dist     = {node: INF for node in self.graph}
        prev     = {node: None for node in self.graph}
        dist[source] = 0.0

        # Min-heap: (tentative_distance, node_name)
        heap = [(0.0, source)]
        visited = set()

        # ── Main loop ─────────────────────────────────────────────────────────
        while heap:
            current_dist, u = heapq.heappop(heap)

            # Early termination — we reached the target
            if u == target:
                break

            # Skip if we've already processed this node with a shorter path
            if u in visited:
                continue
            visited.add(u)

            # Relax each outgoing edge
            for v, edge_data in self.graph[u].items():
                if v in visited:
                    continue
                new_dist = current_dist + edge_data["weight"]
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(heap, (new_dist, v))

        # ── Reconstruct path ──────────────────────────────────────────────────
        if dist[target] == INF:
            return {
                "found":    False,
                "error":    f"No path from '{source}' to '{target}'",
                "path":     [],
                "total_weight": INF,
            }

        path = []
        node = target
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()

        # ── Build edge details for frontend / visualization ───────────────────
        edges_used         = []
        total_distance_km  = 0.0

        for i in range(len(path) - 1):
            a    = path[i]
            b    = path[i + 1]
            data = self.graph[a][b]
            total_distance_km += data["distance"]
            edges_used.append({
                "from":       a,
                "to":         b,
                "road_id":    data["road_id"],
                "distance_km": data["distance"],
                "congestion": data.get("congestion", "Unknown"),
                "weight":     data["weight"],
            })

        # Estimate time in minutes (base speed 40 km/h, adjusted by weight)
        estimated_minutes = round((dist[target] / 40) * 60, 1)

        return {
            "found":              True,
            "path":               path,
            "total_weight":       round(dist[target], 4),
            "total_distance_km":  round(total_distance_km, 2),
            "estimated_minutes":  estimated_minutes,
            "edges_used":         edges_used,
        }

    def get_all_edges_info(self) -> list:
        """Returns all edges with their current weights and congestion levels."""
        seen   = set()
        result = []
        for a, neighbors in self.graph.items():
            for b, data in neighbors.items():
                key = tuple(sorted([a, b]) + [data["road_id"]])
                if key not in seen:
                    seen.add(key)
                    result.append({
                        "from":       a,
                        "to":         b,
                        "road_id":    data["road_id"],
                        "distance_km": data["distance"],
                        "congestion": data.get("congestion", "Unknown"),
                        "weight":     data["weight"],
                    })
        return result

    def get_nodes(self) -> list:
        return list(self.graph.keys())
