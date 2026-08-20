#!/usr/bin/env python3
"""
Adjacency Matrix vs Adjacency List Experiment
Measures has_edge(), get_neighbors(), and memory usage across
different V and densities.
"""

import time
import random
import sys
import gc
import tracemalloc
from typing import List, Tuple, Dict, Any
import numpy as np

# ============================================================
# Graph Representations
# ============================================================

class AdjacencyMatrix:
    def __init__(self, n: int):
        self.n = n
        # Use numpy for efficiency and accurate memory
        self.matrix = np.zeros((n, n), dtype=np.uint8)

    def add_edge(self, u: int, v: int):
        if u == v:
            return
        self.matrix[u][v] = 1
        self.matrix[v][u] = 1  # undirected

    def has_edge(self, u: int, v: int) -> bool:
        return self.matrix[u][v] == 1

    def get_neighbors(self, u: int) -> List[int]:
        return [v for v in range(self.n) if self.matrix[u][v] == 1]

    def memory_bytes(self) -> int:
        return self.matrix.nbytes


class AdjacencyList:
    def __init__(self, n: int):
        self.n = n
        self.adj: List[List[int]] = [[] for _ in range(n)]

    def add_edge(self, u: int, v: int):
        if u == v:
            return
        # No membership check: generate_edges() already guarantees unique
        # (u, v) pairs via a set, so an O(deg) scan here would only add
        # construction cost for no benefit. (An earlier version did check,
        # and that scan was the bottleneck behind an incomplete first run
        # at the largest/densest V×density combinations — see README.)
        self.adj[u].append(v)
        self.adj[v].append(u)

    def has_edge(self, u: int, v: int) -> bool:
        return v in self.adj[u]

    def get_neighbors(self, u: int) -> List[int]:
        return list(self.adj[u])  # return a copy to be fair

    def memory_bytes(self) -> int:
        # Approximate: list of lists + integers
        # Each list has overhead + 8 bytes per int (approx on 64-bit)
        total = sys.getsizeof(self.adj)
        for lst in self.adj:
            total += sys.getsizeof(lst)
            total += len(lst) * 8  # rough int size
        return total


# ============================================================
# Graph Generation (identical edge set for both representations)
# ============================================================

def generate_edges(n: int, density: float, seed: int = 42) -> List[Tuple[int, int]]:
    """Generate undirected edges for a simple graph with given density.
    Density = 2E / (V*(V-1)) for undirected simple graph.
    """
    random.seed(seed)
    max_edges = n * (n - 1) // 2
    target_edges = int(density * max_edges)
    edges = set()
    while len(edges) < target_edges:
        u = random.randint(0, n - 1)
        v = random.randint(0, n - 1)
        if u != v:
            a, b = min(u, v), max(u, v)
            edges.add((a, b))
    return list(edges)


def build_both(n: int, edges: List[Tuple[int, int]]):
    mat = AdjacencyMatrix(n)
    lst = AdjacencyList(n)
    for u, v in edges:
        mat.add_edge(u, v)
        lst.add_edge(u, v)
    return mat, lst


# ============================================================
# Measurement Helpers
# ============================================================

def measure_has_edge(rep, n: int, num_ops: int = 100_000) -> float:
    """Average time per has_edge call (seconds)."""
    # Pre-generate pairs
    pairs = [(random.randint(0, n-1), random.randint(0, n-1)) for _ in range(num_ops)]
    # Warm-up
    for _ in range(min(500, num_ops // 10)):
        u, v = pairs[_ % len(pairs)]
        _ = rep.has_edge(u, v)
    gc.collect()
    start = time.perf_counter()
    for u, v in pairs:
        _ = rep.has_edge(u, v)
    end = time.perf_counter()
    return (end - start) / num_ops


def measure_get_neighbors(rep, n: int, num_ops: int = 5_000) -> float:
    """Average time per get_neighbors call (seconds)."""
    vertices = [random.randint(0, n-1) for _ in range(num_ops)]
    # Warm-up
    for _ in range(min(100, num_ops // 10)):
        _ = rep.get_neighbors(vertices[_ % len(vertices)])
    gc.collect()
    start = time.perf_counter()
    for u in vertices:
        _ = rep.get_neighbors(u)
    end = time.perf_counter()
    return (end - start) / num_ops


def measure_memory(rep) -> int:
    """Return approximate memory in bytes."""
    if isinstance(rep, AdjacencyMatrix):
        return rep.memory_bytes()
    else:
        return rep.memory_bytes()


# ============================================================
# Experiment Runner
# ============================================================

def run_experiments():
    sizes = [100, 500, 1000, 2000, 5000]
    densities = [0.001, 0.01, 0.10, 0.50, 0.90]  # 0.1%, 1%, 10%, 50%, 90%

    results = []

    print("=" * 80)
    print("Starting experiments...")
    print("=" * 80)

    for V in sizes:
        for dens in densities:
            print(f"\n>>> V={V}, Density={dens*100:.1f}%")
            edges = generate_edges(V, dens, seed=42 + V)
            E = len(edges)
            actual_density = 2 * E / (V * (V - 1)) if V > 1 else 0
            print(f"    Generated E={E}, actual density={actual_density*100:.3f}%")

            mat, lst = build_both(V, edges)

            # Memory
            mem_mat = measure_memory(mat)
            mem_lst = measure_memory(lst)

            # has_edge
            has_ops = 100_000 if V <= 1000 else (30_000 if V <= 2000 else 10_000)
            t_has_mat = measure_has_edge(mat, V, has_ops)
            t_has_lst = measure_has_edge(lst, V, has_ops)

            # get_neighbors - Matrix is O(V), so fewer calls for large V
            neigh_ops = 10_000 if V <= 500 else (2_000 if V <= 2000 else 500)
            t_nei_mat = measure_get_neighbors(mat, V, neigh_ops)
            t_nei_lst = measure_get_neighbors(lst, V, neigh_ops)

            # Record
            for rep_name, t_has, t_nei, mem in [
                ("Matrix", t_has_mat, t_nei_mat, mem_mat),
                ("List", t_has_lst, t_nei_lst, mem_lst),
            ]:
                results.append({
                    "Representation": rep_name,
                    "V": V,
                    "Density": dens,
                    "E": E,
                    "ActualDensity": actual_density,
                    "has_edge_ns": t_has * 1e9,      # nanoseconds
                    "get_neighbors_ns": t_nei * 1e9,
                    "Memory_bytes": mem,
                    "Memory_KB": mem / 1024,
                    "Memory_MB": mem / (1024 * 1024),
                })

            print(f"    Matrix: has={t_has_mat*1e9:.1f}ns  nei={t_nei_mat*1e9:.1f}ns  mem={mem_mat/1024:.1f}KB")
            print(f"    List  : has={t_has_lst*1e9:.1f}ns  nei={t_nei_lst*1e9:.1f}ns  mem={mem_lst/1024:.1f}KB")

            # Cleanup
            del mat, lst, edges
            gc.collect()

    return results


def save_results(results, path="results.csv"):
    import csv
    keys = ["Representation", "V", "Density", "E", "ActualDensity",
            "has_edge_ns", "get_neighbors_ns", "Memory_bytes", "Memory_KB", "Memory_MB"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"\nResults saved to {path}")


if __name__ == "__main__":
    results = run_experiments()
    save_results(results, "/home/workdir/artifacts/results.csv")
    print("\nDone.")
