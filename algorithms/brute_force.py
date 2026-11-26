from itertools import combinations


def solve(instance, seed=42):
    universe = instance["universe"]
    subsets = instance["subsets"]

    # 1. Feasibility: if even all subsets together miss an element,
    #    no cover exists. One cheap test avoids a useless 2^m search.
    union_of_all = set()
    for subset in subsets:
        union_of_all |= subset
    if not universe <= union_of_all:
        return None

    # 2. Sizes k = 0, 1, ..., m. k = 0 handles the empty universe:
    #    the empty selection covers the empty set.
    selected_subsets = None
    m = len(subsets)
    for k in range(m + 1):
        for combo in combinations(range(m), k):
            covered = set()
            for i in combo:
                covered |= subsets[i]
            if universe <= covered:          # every element is covered
                selected_subsets = list(combo)
                return selected_subsets

    # Never reached: a feasible instance is covered at k = m at the latest.
    return selected_subsets


if __name__ == "__main__":
    instance = {
        "universe": {0, 1, 2, 3, 4},
        "subsets": [
            {0, 1, 2},   # Subset 0
            {2, 3},      # Subset 1
            {3, 4},      # Subset 2
            {0, 4},      # Subset 3
        ],
    }
    print(solve(instance))  # expected: [0, 2]
