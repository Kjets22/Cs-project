#!/usr/bin/env python3
import sys

def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(parent, rank, x, y):
    xroot = find(parent, x)
    yroot = find(parent, y)
    if xroot == yroot:
        return False
    if rank[xroot] < rank[yroot]:
        parent[xroot] = yroot
    elif rank[xroot] > rank[yroot]:
        parent[yroot] = xroot
    else:
        parent[yroot] = xroot
        rank[xroot] += 1
    return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python mst_semiexternal.py <input_edge_list.csv>")
        sys.exit(1)

    input_path = sys.argv[1]
    max_vertex = 0
    with open(input_path) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) != 3:
                continue
            u, v, _ = map(int, parts)
            if u > max_vertex:
                max_vertex = u
            if v > max_vertex:
                max_vertex = v
    n = max_vertex

    parent = list(range(n+1))
    rank = [0] * (n+1)
    mst_edges = []
    rounds = 0

    while len(mst_edges) < n - 1:
        rounds += 1
        best = {}
        with open(input_path) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) != 3:
                    continue
                u, v, w = map(int, parts)
                ru, rv = find(parent, u), find(parent, v)
                if ru == rv: 
                    continue
                if ru not in best or w < best[ru][2]: 
                    best[ru] = (u, v, w)
                if rv not in best or w < best[rv][2]: 
                    best[rv] = (u, v, w)
        if not best: 
            break
        for u, v, w in best.values():
            if len(mst_edges) >= n - 1: 
                break
            if union(parent, rank, u, v):
                mst_edges.append((u, v, w))

    total_weight = sum(w for _, _, w in mst_edges)

    with open("size.txt", "w") as f:
        for u, v, w in mst_edges:
            f.write(f"{u},{v},{w}\n")
        f.write(f"num_vertices: {n}\n")
        f.write(f"num_edges: {len(mst_edges)}\n")
        f.write(f"total_weight: {total_weight}\n")

    passes_read = 1 + rounds
    passes_write = 2
    with open("io.txt", "w") as f:
        f.write(f"passes_read: {passes_read}\n")
        f.write(f"passes_write: {passes_write}\n")

    print(f"MST: {len(mst_edges)} edges, {n} vertices")
    print(f"Total weight: {total_weight}")
    print(f"I/O passes_read: {passes_read}, passes_write: {passes_write}")

if __name__ == '__main__':
    main()
