# greedy_set_cover.py

import sys

def read_pairs(path):
    """
    Reads a file where each non-blank line is "u,v".
    Returns:
      edges: list of (u, v) tuples
      universe: set of all vertices
    """
    edges = []
    universe = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            u_str, v_str = line.split(",", 1)
            u, v = int(u_str), int(v_str)
            edges.append((u, v))
            universe.add(u)
            universe.add(v)
    return edges, universe

def greedy_cover(edges, universe):
    """
    Standard greedy set‑cover on 2‑element sets (edges).
    """
    uncovered = set(universe)
    cover = []
    edge_sets = [frozenset(e) for e in edges]

    while uncovered:
        # pick the edge covering most uncovered vertices
        best_idx, best_gain = None, -1
        for i, s in enumerate(edge_sets):
            gain = len(s & uncovered)
            if gain > best_gain:
                best_idx, best_gain = i, gain
        if best_gain == 0:
            break
        cover.append(edges[best_idx])
        uncovered -= edge_sets[best_idx]

    return cover

def write_cover(path, cover):
    """
    Writes the cover to 'greedy.txt':
      first line = number of edges
      each subsequent line = "u v"
    """
    with open(path, "w") as f:
        f.write(f"{len(cover)}\n")
        for u, v in cover:
            f.write(f"{u} {v}\n")

def main():
    if len(sys.argv) != 2:
        print("Usage: python greedy_set_cover.py <input.txt>")
        sys.exit(1)

    edges, universe = read_pairs(sys.argv[1])
    cover = greedy_cover(edges, universe)
    write_cover("greedy.txt", cover)

if __name__ == "__main__":
    main()
