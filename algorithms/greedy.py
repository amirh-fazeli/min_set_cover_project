def solve(instance, seed=42):

    # Get the universe and subsets
    universe = instance["universe"]
    subsets = instance["subsets"]

    # Initially, nothing is covered
    uncovered = set(universe)

    # Store selected subset indices
    selected_subsets = []

    # Keep selecting subsets until everything is covered
    while uncovered:

        best_index = None
        best_gain = 0

        # Check every available subset
        for i, subset in enumerate(subsets):

            # Do not select a subset twice
            if i in selected_subsets:
                continue

            # Count newly covered elements
            new_elements = uncovered.intersection(subset)
            gain = len(new_elements)

            # Keep the subset with the highest gain
            if gain > best_gain:
                best_gain = gain
                best_index = i

        # No remaining subset can cover the uncovered elements
        if best_index is None:
            raise ValueError("No complete cover exists for this instance.")

        # Select the best subset
        selected_subsets.append(best_index)

        # Remove its elements from the uncovered set
        uncovered -= subsets[best_index]

    return selected_subsets
