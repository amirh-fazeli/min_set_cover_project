import random


def solve(instance, seed=42):

    # Initialize random number generator
    rng = random.Random(seed)

    # Get the universe and subsets
    universe = instance["universe"]
    subsets = instance["subsets"]

    # Initially, all elements are uncovered
    uncovered = set(universe)

    # Store selected subset indices
    selected_subsets = []

    # Randomization parameter
    alpha = 0.80

    # Continue until everything is covered
    while uncovered:

        gains = []

        # Calculate the gain of every available subset
        for i, subset in enumerate(subsets):

            if i in selected_subsets:
                continue

            gain = len(uncovered.intersection(subset))

            if gain > 0:
                gains.append((i, gain))

        # Check whether a complete cover is possible
        if not gains:
            raise ValueError("No complete cover exists for this instance.")

        # Find the maximum gain
        max_gain = max(gain for i, gain in gains)

        # Build the restricted candidate list
        candidates = [
            i for i, gain in gains
            if gain >= alpha * max_gain
        ]

        # Randomly select one candidate
        chosen_index = rng.choice(candidates)

        # Add it to the solution
        selected_subsets.append(chosen_index)

        # Update uncovered elements
        uncovered -= subsets[chosen_index]

    return selected_subsets
