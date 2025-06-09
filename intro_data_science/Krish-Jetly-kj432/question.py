import numpy as np

def load_graph(file_path):
    with open(file_path, 'r') as f:
        edges = [tuple(map(int, line.strip().split())) for line in f.readlines()]
    return edges

def build_transition_matrix(edges, n):
    M = np.zeros((n, n))
    out_degree = [0] * n
    for src, dest in edges:
        M[dest-1, src-1] += 1   
        out_degree[src-1] += 1
    for i in range(n):
        if out_degree[i] > 0:
            M[:, i] /= out_degree[i]
    return M

def pagerank(M, beta, iterations):
    n = M.shape[0]
    r = np.ones(n) / n
    teleport = (1 - beta) / n
    for _ in range(iterations):
        r = teleport + beta * M @ r
    return r

if __name__ == "__main__":
    edges = load_graph("graph.txt")
    n = 100
    beta = 0.8
    iterations = 40
    M = build_transition_matrix(edges, n)
    ranks = pagerank(M, beta, iterations)
    
    sorted_indices = np.argsort(ranks)
    
    # Sort top 5 and bottom 5 nodes by their scores
    top_5 = sorted(sorted_indices[-5:], key=lambda x: -ranks[x])
    bottom_5 = sorted(sorted_indices[:5], key=lambda x: -ranks[x])
    
    print("Top 5 nodes with scores:")
    for node in top_5:
        print(f"Node {node + 1}: PageRank {ranks[node]:.6f}")
    
    print("\nBottom 5 nodes with scores:")
    for node in bottom_5:
        print(f"Node {node + 1}: PageRank {ranks[node]:.6f}")
