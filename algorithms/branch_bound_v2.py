
from math import ceil


def solve(instance, seed=42):
    universe = set(instance["universe"])
    subsets = [set(s) for s in instance["subsets"]]

    if not universe:
        return []

    # Check whether a cover exists
    if not universe.issubset(set().union(*subsets)):
        return None

    # Initial upper bound from Greedy
    uncovered = universe.copy()
    best_solution = []

    while uncovered:
        i = max(
            range(len(subsets)),
            key=lambda j: len(subsets[j] & uncovered)
        )
        best_solution.append(i)
        uncovered -= subsets[i]

    best_size = len(best_solution)

    def search(uncovered, available, selected):
        nonlocal best_solution, best_size

        # Found a complete cover
        if not uncovered:
            if len(selected) < best_size:
                best_solution = selected.copy()
                best_size = len(selected)
            return

        if len(selected) >= best_size:
            return

        # Remove useless and dominated subsets
        useful = sorted(
            (
                (i, subsets[i] & uncovered)
                for i in available
                if subsets[i] & uncovered
            ),
            key=lambda pair: (-len(pair[1]), pair[0])
        )

        reduced = {}

        for i, coverage in useful:
            if not any(
                coverage <= kept
                for kept in reduced.values()
            ):
                reduced[i] = coverage

        # Check whether all elements remain coverable
        possible = set().union(*reduced.values())

        if not uncovered.issubset(possible):
            return

        # Identify forced subsets
        covering = {
            e: [
                i for i, coverage in reduced.items()
                if e in coverage
            ]
            for e in uncovered
        }

        if any(not options for options in covering.values()):
            return

        forced = next(
            (
                options[0]
                for options in covering.values()
                if len(options) == 1
            ),
            None
        )

        if forced is not None:
            return search(
                uncovered - reduced[forced],
                set(reduced) - {forced},
                selected + [forced]
            )

        # Coverage-based lower bound
        max_gain = max(len(s) for s in reduced.values())
        lb_coverage = ceil(len(uncovered) / max_gain)

        # Additional packing lower bound
        packed_choices = set()
        lb_packing = 0

        for _, options in sorted(
            covering.items(),
            key=lambda pair: len(pair[1])
        ):
            option_set = set(options)

            if packed_choices.isdisjoint(option_set):
                packed_choices.update(option_set)
                lb_packing += 1

        lower_bound = max(lb_coverage, lb_packing)

        if len(selected) + lower_bound >= best_size:
            return

        # Choose the most-constrained uncovered element
        element = min(
            uncovered,
            key=lambda e: len(covering[e])
        )

        # Branch over subsets that can cover it
        choices = sorted(
            covering[element],
            key=lambda i: (-len(reduced[i]), i)
        )

        for i in choices:
            search(
                uncovered - reduced[i],
                set(reduced) - {i},
                selected + [i]
            )

    search(universe, set(range(len(subsets))), [])

    return best_solution
