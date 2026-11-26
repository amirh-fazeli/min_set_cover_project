import random
from itertools import combinations


def build_containing(subsets):
    containing = {}
    for t, subset in enumerate(subsets):
        for element in subset:
            containing.setdefault(element, []).append(t)
    return containing


def coverage_count(subsets, solution):
    count = {}
    for i in solution:
        for element in subsets[i]:
            count[element] = count.get(element, 0) + 1
    return count


# ---------------------------------------------------------------------------
# Building blocks of the local search
# ---------------------------------------------------------------------------

def greedy_complete(universe, subsets, solution, banned):
    selected = list(solution)
    chosen = set(selected)

    uncovered = set(universe)
    for i in selected:
        uncovered -= subsets[i]

    while uncovered:
        best_index, best_gain = None, 0
        for t, subset in enumerate(subsets):
            if t in chosen or t in banned:
                continue
            gain = len(subset & uncovered)
            if gain > best_gain:
                best_index, best_gain = t, gain
        if best_index is None:          # nothing can cover what is left
            return None
        selected.append(best_index)
        chosen.add(best_index)
        uncovered -= subsets[best_index]
    return selected


def remove_redundant(subsets, solution):
    solution = list(solution)
    count = coverage_count(subsets, solution)
    for i in sorted(solution, key=lambda idx: (len(subsets[idx]), idx)):
        if all(count[element] >= 2 for element in subsets[i]):
            solution.remove(i)
            for element in subsets[i]:
                count[element] -= 1
    return solution


def swap_two_for_one(subsets, solution, containing):
    count = coverage_count(subsets, solution)
    in_solution = set(solution)

    for a, b in combinations(solution, 2):
        set_a, set_b = subsets[a], subsets[b]
        # Element e is lost if a and b are its only covering subsets:
        # count[e] minus (1 if a covers it) minus (1 if b covers it) == 0.
        missing = {e for e in set_a | set_b
                   if count[e] - (e in set_a) - (e in set_b) == 0}
        rest = [i for i in solution if i != a and i != b]
        if not missing:                  # a and b can both go: gain of 2
            return rest
        e = min(missing)                 # min() keeps the result deterministic
        for t in containing[e]:
            if t not in in_solution and missing <= subsets[t]:
                return rest + [t]
    return None


def descent(subsets, solution, containing):
    solution = remove_redundant(subsets, solution)
    while True:
        swapped = swap_two_for_one(subsets, solution, containing)
        if swapped is None:
            return solution
        solution = remove_redundant(subsets, swapped)


def kick(universe, subsets, solution, j, containing):
    without_j = [i for i in solution if i != j]
    refilled = greedy_complete(universe, subsets, without_j, banned={j})
    if refilled is None:
        return None
    return descent(subsets, refilled, containing)


# ---------------------------------------------------------------------------
# Common interface
# ---------------------------------------------------------------------------

def solve(instance, seed=42):
    universe = instance["universe"]
    subsets = instance["subsets"]

    # 1. "Which subsets contain element e" table, and a local random
    #    generator (reproducible, independent from other modules).
    containing = build_containing(subsets)
    rng = random.Random(seed)

    # 2. Greedy start (None means that the instance is infeasible).
    selected_subsets = greedy_complete(universe, subsets, [], banned=set())
    if selected_subsets is None:
        return None

    # 3. Descent from the greedy solution.
    selected_subsets = descent(subsets, selected_subsets, containing)

    # 4. Rounds of kicks until a full round brings no improvement.
    improved = True
    while improved:
        improved = False
        order = list(selected_subsets)
        rng.shuffle(order)
        for j in order:
            candidate = kick(universe, subsets, selected_subsets, j, containing)
            if candidate is not None and len(candidate) < len(selected_subsets):
                selected_subsets = candidate
                improved = True
                break                     # start a new round

    return sorted(selected_subsets)


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
