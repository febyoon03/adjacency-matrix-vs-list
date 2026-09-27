# Adjacency Matrix vs. Adjacency List: Measuring the Textbook Trade-off

*Built for Data Structures, November 2025. Uploaded to GitHub in August 2026.*

The trade-off between the two classic graph representations, in `has_edge()` speed, `get_neighbors()` speed, and memory use, is standard textbook material: $O(1)$ vs $O(\deg)$, and $\Theta(V^2)$ vs $\Theta(V+E)$. Rather than just citing those numbers, this project actually measures them directly, across a range of graph sizes and densities.

## Motivation

The Big-O trade-off here is well known, but Big-O hides the actual constants involved, and those constants matter a lot in practice. A Python list membership check and a NumPy array index lookup are both technically "O(something)," but they run at very different real speeds. This project measures actual wall-clock time and real memory use, not just theoretical complexity, so the crossover points reported here are measured, not just assumed from theory.

## Approach

Both representations were built from the exact same randomly generated set of edges each time, so the comparison stays fair. This was repeated across graph sizes V of 100, 500, 1000, 2000, and 5000, and densities of 0.1%, 1%, 10%, 50%, and 90%, giving 25 size-and-density combinations in total, or 50 result rows. For each combination, `has_edge()` was timed over up to 100,000 random queries, and `get_neighbors()` was timed over up to 10,000 random queries (fewer at large V, since the matrix's $O(V)$ scan gets expensive there). Memory was measured directly: `nbytes` for the NumPy matrix, and `sys.getsizeof` summed across the list-of-lists for the adjacency list.

**A first run of this experiment didn't finish.** Three of the 25 combinations, at V=2000/90%, V=5000/50%, and V=5000/90%, never completed. There were three compounding causes. `AdjacencyList.add_edge()` originally checked `if v not in self.adj[u]` before inserting, an $O(\text{current degree})$ scan that gets slow once the lists get long. The edge generator's rejection sampling (retrying until it finds a unique edge) also gets slower as the target density climbs and collisions become more frequent. And at V=5000/90%, the intermediate list of roughly 11.2 million edge pairs is itself a huge amount of Python object overhead before either graph structure has even been built. Since the edge generator already guarantees unique pairs through a `set()`, the membership check inside `add_edge()` turned out to be pure waste. Removing those two `if ... not in ...` checks, while keeping the two `.append()` calls, was enough to let all 25 combinations finish. That fix is reflected in `graph_experiment.py` as committed here; see the code comment at `AdjacencyList.add_edge()`.

## Results

**Sparse graphs (0.1% density): the list wins on everything.**

| V | Matrix has_edge | List has_edge | Matrix get_neighbors | List get_neighbors | Matrix mem | List mem |
|---|---|---|---|---|---|---|
| 100 | 194.7ns | 40.1ns | 16.5µs | 61.6ns | 9.8KB | 6.7KB |
| 1000 | 254.2ns | 95.7ns | 188.4µs | 108.1ns | 976.6KB | 90.8KB |
| 5000 | 336.7ns | 138.5ns | 963.5µs | 300.8ns | 23.8MB | 772.5KB |

**Dense graphs (50-90% density): the matrix wins on `has_edge()` and memory, but the list still wins on `get_neighbors()`.**

| V, density | Matrix has_edge | List has_edge | Matrix get_neighbors | List get_neighbors | Matrix mem | List mem |
|---|---|---|---|---|---|---|
| 1000, 50% | 270.6ns | 6,800.6ns (**~25x slower**) | 194.7µs | 7,085.7ns (**~27x faster**) | 976.6KB | 8,079.2KB (**~8x more**) |
| 2000, 90% | 398.8ns | 43,826.8ns (**~110x slower**) | 358.4µs | 32,617.5ns (**~11x faster**) | 3,906.2KB | 58,959.5KB (**~15x more**) |
| 5000, 90% | 920.5ns | 25,419.7ns (**~28x slower**) | 893.6µs | 47,020.2ns (**~19x faster**) | 23,414.1KB | 353,246.0KB (**~15x more**) |

The **memory crossover point** happens earlier at larger V. At V=2000, the list overtakes the matrix in memory use somewhere between 1% and 10% density (0.79MB growing to 6.45MB, against the matrix's flat 3.81MB). At V=5000, it has already crossed over by 10% density (38.7MB against the matrix's flat 23.8MB), and by 90% density the list uses **345MB compared to the matrix's 23.8MB**, nearly 15 times more, purely from the per-object overhead of Python lists.

**Takeaway.** The textbook trade-off mostly holds, with one twist. `has_edge()` speed and memory use behave exactly as theory predicts: the list wins when sparse, the matrix wins when dense, and the memory crossover point moves earlier (to a lower density) as V grows. But `get_neighbors()` never actually crosses over in this data. The list stays faster even at 90% density, because this matrix implementation has to do a Python-level scan across all V columns (`[v for v in range(n) if matrix[u][v]]`), while the list just does `list(self.adj[u])`, a fast copy of however many neighbors actually exist. That's an implementation detail, not a fundamental $O(\cdot)$ effect. A vectorized NumPy call like `np.nonzero(matrix[u])` would likely close most of that gap, but this version doesn't do that.

**Practical conclusion.** Use an adjacency list for sparse graphs. Use an adjacency matrix (or a bit-packed matrix, for memory) for dense graphs, roughly 20-40% density and above, or for workloads that are heavy on `has_edge()` calls. For workloads that are heavy on `get_neighbors()` calls, the list wins even when the graph is dense, at least with an implementation this straightforward.

## Tech stack

Python, NumPy.

## How to run it

```bash
pip install numpy
python graph_experiment.py
```

This runs the full 25-combination grid of V and density, and writes the results to `results.csv`. The largest and densest combinations (V=5000, density 50% and above) take noticeably longer to run, since just the intermediate list of edge pairs already has millions of entries.

## Limitations and what's next

The matrix's `get_neighbors()` uses a plain Python list comprehension rather than a vectorized NumPy call, so the result that "the list wins even when dense" is at least partly an artifact of that choice, not a fundamental property of the matrix representation itself.

These timings are wall-clock measurements from a single machine and a single run, not averaged across multiple runs. The overall pattern is consistent and matches theory, but a few individual results (for example, V=2000/90% `has_edge` landing slightly higher than V=5000/90%) show some non-monotonic noise that averaging across multiple runs would likely smooth out.

The edge generator's rejection sampling gets slower as the target density approaches the maximum possible number of edges. A direct combinatorial sampling method would scale better at very high density and large V, though it wasn't strictly necessary once the `add_edge()` bottleneck was fixed.

## Credits

Built independently, with no external code reused beyond NumPy itself.
