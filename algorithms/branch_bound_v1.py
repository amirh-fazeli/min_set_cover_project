
from math import ceil


def solve(instance, seed=42):
    universe = set(instance["universe"])
    subsets = [set(s) for s in instance["subsets"]]

    if not universe:
        return []

    # Check whether a solution exists
    if not universe.issubset(set().union(*subsets)):
        return None

    # Sort subsets by descending coverage
    order = sorted(
        range(len(subsets)),
        key=lambda i: len(subsets[i]),
        reverse=True
    )

    # Initial Greedy solution
    uncovered = universe.copy()
    best_solution = []

    while uncovered:
        best = max(
            range(len(subsets)),
            key=lambda i: len(subsets[i] & uncovered)
        )

        best_solution.append(best)
        uncovered -= subsets[best]

    best_size = len(best_solution)

    # Recursive Branch-and-Bound
    def branch(pos, covered, selected):
        nonlocal best_solution, best_size

        if universe.issubset(covered):
            if len(selected) < best_size:
                best_solution = selected.copy()
                best_size = len(selected)
            return

        if pos == len(order):
            return

        uncovered = universe - covered
        remaining = order[pos:]

        # Feasibility pruning
        possible = set()
        for i in remaining:
            possible.update(subsets[i])

        if not uncovered.issubset(possible):
            return

        # Lower bound
        max_cover = max(
            len(subsets[i] & uncovered)
            for i in remaining
        )

        if max_cover == 0:
            return

        lower_bound = ceil(
            len(uncovered) / max_cover
        )

        # Bound pruning
        if len(selected) + lower_bound >= best_size:
            return

        current = order[pos]

        # Include current subset
        branch(
            pos + 1,
            covered | subsets[current],
            selected + [current]
        )

        # Exclude current subset
        branch(
            pos + 1,
            covered,
            selected
        )

    branch(0, set(), [])

    return best_solution
