import numpy as np

def calculate_modularity(adj_matrix, communities):
    m = np.sum(adj_matrix) / 2
    Q = 0
    for i in range(len(adj_matrix)):
        ki = np.sum(adj_matrix[i])
        for j in range(len(adj_matrix)):
            Aij = adj_matrix[i][j]
            kj = np.sum(adj_matrix[j])
            delta = 1 if communities[i] == communities[j] else 0
            Q += (Aij - (ki * kj) / (2 * m)) * delta
    return Q / (4 * m)

if __name__ == "__main__":
    # Original adjacency matrix
    original_adj = np.array([
        # A  B  C  D  E  F  G  H
        [0, 1, 1, 1, 0, 0, 1, 0],  # A
        [1, 0, 1, 1, 0, 0, 0, 0],  # B
        [1, 1, 0, 1, 0, 0, 0, 0],  # C
        [1, 1, 1, 1, 0, 0, 0, 0],  # D
        [0, 0, 0, 0, 0, 1, 1, 0],  # E
        [0, 0, 0, 0, 1, 0, 1, 0],  # F
        [1, 0, 0, 0, 1, 1, 0, 1],  # G
        [0, 0, 0, 0, 0, 0, 1, 0],  # H
    ])
    communities = [0, 0, 0, 0, 1, 1, 1, 1]

    # Calculate the original modularity
    Q_original = calculate_modularity(original_adj, communities)
    print("Original Modularity (Q):", Q_original)

    # (a) Remove edge (A, G)
    adj_a = original_adj.copy()
    adj_a[0, 6] = adj_a[6, 0] = 0
    Q_a = calculate_modularity(adj_a, communities)
    print("(a) After removing (A,G):")
    print("    Old Q:", Q_original)
    print("    New Q:", Q_a)

    # (b) Add edge (E, H) starting from the original network
    adj_b = original_adj.copy()
    adj_b[4, 7] = adj_b[7, 4] = 1
    Q_b = calculate_modularity(adj_b, communities)
    print("(b) After adding (E,H):")
    print("    Old Q:", Q_original)
    print("    New Q:", Q_b)

    # (c) Add edge (F, A) starting from the original network
    adj_c = original_adj.copy()
    adj_c[5, 0] = adj_c[0, 5] = 1
    Q_c = calculate_modularity(adj_c, communities)
    print("(c) After adding (F,A):")
    print("    Old Q:", Q_original)
    print("    New Q:", Q_c)



