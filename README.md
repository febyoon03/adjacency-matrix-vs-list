# Adjacency Matrix vs. Adjacency List: Measuring the Textbook Trade-off

*Built for Data Structure, November 2025. Uploaded to GitHub in August 2026.*

The has_edge() / get_neighbors() / memory trade-off between the two classic graph representations is standard textbook material (O(1) vs O(deg), Θ(V²) vs Θ(V+E)) — this measures it directly instead of citing it, across a range of graph sizes and densities.

## Motivation

The Big-O trade-off is well known, but Big-O hides constants, and constants matter a lot in practice — a Python list membership check and a NumPy array index are both "O(something)" but run at very different actual speeds. This measures wall-clock time and real memory, not asymptotic complexity, so the crossover points are empirical, not theoretical.

## Approach

Both representations built from the *same* randomly generated edge set (so the comparison is apples-to-apples), across V ∈ {100, 500, 1000, 2000, 5000} and density ∈ {0.1%, 1%, 10%, 50%, 90%} — 25 V×density combinations, 50 rows total. For each combination: `has_edge()` timed over up to 100,000 random queries, `get_neighbors()` timed over up to 10,000 random queries (fewer at large V since Matrix's O(V) scan gets expensive), and memory measured directly (`nbytes` for the NumPy matrix; `sys.getsizeof` summed across the list-of-lists for the adjacency list).

**A first run didn't finish.** Three of the 25 combinations — V=2000/90%, V=5000/50%, V=5000/90% — never completed. Three compounding causes: `AdjacencyList.add_edge()` originally checked `if v not in self.adj[u]` before inserting, an O(current-degree) scan that gets expensive once lists get long; the edge generator's rejection sampling (retry-until-unique) degrades as target density climbs and collisions get more frequent; and at V=5000/90% the intermediate list of ~11.2M edge tuples is itself a lot of Python object overhead before either graph structure is even built. The edge generator already guarantees unique pairs via a `set()`, so the membership check in `add_edge()` was pure waste — removing it (the two `if ... not in ...` checks, keeping the two `.append()` calls) was enough to let all 25 combinations finish. That fix is reflected in `graph_experiment.py` as committed here; see the code comment at `AdjacencyList.add_edge()`.

## Results

**Sparse graphs (density 0.1%) — List wins on everything:**

| V | Matrix has_edge | List has_edge | Matrix get_neighbors | List get_neighbors | Matrix mem | List mem |
|---|---|---|---|---|---|---|
| 100 | 194.7ns | 40.1ns | 16.5µs | 61.6ns | 9.8KB | 6.7KB |
| 1000 | 254.2ns | 95.7ns | 188.4µs | 108.1ns | 976.6KB | 90.8KB |
| 5000 | 336.7ns | 138.5ns | 963.5µs | 300.8ns | 23.8MB | 772.5KB |

**Dense graphs (density 50-90%) — Matrix wins on has_edge and memory; List still wins on get_neighbors:**

| V, density | Matrix has_edge | List has_edge | Matrix get_neighbors | List get_neighbors | Matrix mem | List mem |
|---|---|---|---|---|---|---|
| 1000, 50% | 270.6ns | 6,800.6ns (**~25x slower**) | 194.7µs | 7,085.7ns (**~27x faster**) | 976.6KB | 8,079.2KB (**~8x more**) |
| 2000, 90% | 398.8ns | 43,826.8ns (**~110x slower**) | 358.4µs | 32,617.5ns (**~11x faster**) | 3,906.2KB | 58,959.5KB (**~15x more**) |
| 5000, 90% | 920.5ns | 25,419.7ns (**~28x slower**) | 893.6µs | 47,020.2ns (**~19x faster**) | 23,414.1KB | 353,246.0KB (**~15x more**) |

**Memory crossover** happens earlier at larger V: at V=2000 the List overtakes the Matrix in memory use somewhere between 1% and 10% density (0.79MB → 6.45MB vs. Matrix's flat 3.81MB); at V=5000 it's already crossed by 10% (38.7MB vs. Matrix's flat 23.8MB), and by 90% density the List uses **345MB vs. the Matrix's 23.8MB** for the same graph — nearly 15x more, purely from Python per-object list overhead.

**Takeaway:** the textbook trade-off holds, with one twist. `has_edge()` and memory behave exactly as the theory predicts: List wins sparse, Matrix wins dense, with memory's crossover point moving earlier (lower density) as V grows. But `get_neighbors()` never actually crosses over in this data — List stays faster even at 90% density, because Matrix's implementation has to do a Python-level scan over all V columns (`[v for v in range(n) if matrix[u][v]]`) while List's is just `list(self.adj[u])`, a fast copy of however many neighbors actually exist. That's an implementation-level effect, not a Big-O one — a vectorized NumPy `np.nonzero(matrix[u])` would likely close most of that gap, and isn't what this version does.

**Practical conclusion:** sparse graphs → adjacency list; dense graphs (roughly 20-40%+ density) or `has_edge()`-heavy workloads → adjacency matrix (or a bit-packed matrix for memory); `get_neighbors()`-heavy workloads favor the list even when dense, at least with this straightforward an implementation.

## Tech stack

Python, NumPy.

## How to run

```bash
pip install numpy
python graph_experiment.py
```
Runs the full 25-combination V × density grid and writes `results.csv`. The largest/densest combinations (V=5000, density≥50%) take noticeably longer — the intermediate edge-tuple list alone is millions of entries.

## Limitations / what's next

- Matrix's `get_neighbors()` uses a Python-level list comprehension rather than a vectorized NumPy call — the "List wins even when dense" result is at least partly an artifact of that, not a fundamental property of the matrix representation itself.
- Timings are wall-clock on a single machine/run, not averaged across multiple runs — the overall pattern is consistent and matches theory, but a few individual cells (e.g. V=2000/90% has_edge landing slightly higher than V=5000/90%) show non-monotonic noise that a multi-run average would likely smooth out.
- The edge generator's rejection sampling gets slower as target density approaches the maximum possible edge count — a direct combinatorial sampling method would scale better at very high density and large V, though it wasn't necessary once the `add_edge()` bottleneck was fixed.

## Credits

Built independently; no external code reused beyond NumPy itself.
