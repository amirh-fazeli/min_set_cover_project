
def solve(instance, seed=42):

    universe = instance["universe"]
    subsets = instance["subsets"]

    elements = sorted(universe)

    position = {
        element: i
        for i, element in enumerate(elements)
    }

    n = len(elements)
    full = (1 << n) - 1

    masks = []

    for subset in subsets:
        mask = 0

        for element in subset:
            mask |= 1 << position[element]

        masks.append(mask)

    INF = float("inf")
    n_states = 1 << n

    dp = [INF] * n_states

    parent_set = [-1] * n_states
    parent_mask = [-1] * n_states

    dp[0] = 0

    for mask in range(n_states):

        if dp[mask] == INF:
            continue

        for i, subset_mask in enumerate(masks):

            new_mask = mask | subset_mask

            if dp[mask] + 1 < dp[new_mask]:

                dp[new_mask] = dp[mask] + 1

                parent_set[new_mask] = i
                parent_mask[new_mask] = mask

    if dp[full] == INF:
        raise ValueError("No feasible cover")

    answer = []
    current = full

    while current != 0:

        answer.append(parent_set[current])
        current = parent_mask[current]

    answer.reverse()

    return answer
