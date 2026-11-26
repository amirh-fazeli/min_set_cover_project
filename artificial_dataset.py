"""Reproducible artificial instances for the unweighted Minimum Set Cover problem."""

import json
import csv
from pathlib import Path
import random


def generate_instance(n: int, m: int, density: float, seed: int = 42) -> dict:
    rng = random.Random(seed)
    universe = set(range(n))
    subsets = [
        {element for element in range(n) if rng.random() < density}
        for _ in range(m)
    ]

    covered = set().union(*subsets)
    for element in sorted(universe - covered):
        subsets[rng.randrange(m)].add(element)

    return {"universe": universe, "subsets": subsets}


def actual_density(instance: dict) -> float:
    """Fraction of all n*m possible element/subset memberships present."""
    n, m = len(instance["universe"]), len(instance["subsets"])
    return sum(map(len, instance["subsets"])) / (n * m) if n and m else 0.0


def validate_instance(instance: dict) -> bool:
    """Check that every element can be covered and subsets contain valid elements."""
    universe, subsets = instance["universe"], instance["subsets"]
    return all(subset <= universe for subset in subsets) and set().union(*subsets) == universe



if __name__ == "__main__":

    # Directory for generated datasets
    output_dir = (
        Path(__file__).resolve().parent
        / "datasets"
        / "artificial"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Five independent instances per configuration
    seeds = [42, 43, 44, 45, 46]

    # Each configuration is (n, m, density)
    experiments = {

        # A: Effect of universe size
        "A_universe_size": [
            (n, 20, 0.20)
            for n in [8, 12, 16, 20, 24, 32]
        ],

        # B: Effect of number of subsets
        "B_subset_count": [
            (16, m, 0.20)
            for m in [8, 12, 20, 40, 80, 160]
        ],

        # C: Effect of density
        "C_density": [
            (16, 20, density)
            for density in [
                0.05, 0.10, 0.20, 0.40, 0.60, 0.80
            ]
        ],

        # D: Effect of universe/subset proportions
        "D_structure": [
            (12, 120, 0.20),
            (120, 12, 0.20),
            (20, 80, 0.20),
            (80, 20, 0.20),
        ],

        # E: Large-scale performance
        "E_scalability": [
            (100, 200, 0.05),
            (500, 500, 0.02),
            (1000, 1000, 0.01),
            (2000, 1000, 0.01),
        ],
    }

    # Group identical configurations to avoid duplicates
    configurations = {}

    for experiment, configs in experiments.items():
        for config in configs:
            configurations.setdefault(config, []).append(
                experiment
            )

    metadata = []

    # Generate all instances
    for (n, m, density), families in configurations.items():

        for seed in seeds:

            instance = generate_instance(
                n=n,
                m=m,
                density=density,
                seed=seed
            )

            # Ensure that the instance is valid
            if not validate_instance(instance):
                raise ValueError(
                    f"Invalid instance: {n}, {m}, {density}, {seed}"
                )

            measured_density = actual_density(instance)

            instance_id = (
                f"n{n}_m{m}_d{density:.2f}_s{seed}"
            )

            filename = f"{instance_id}.json"

            subset_sizes = [
                len(subset)
                for subset in instance["subsets"]
            ]

            # Information describing the instance
            info = {
                "instance_id": instance_id,
                "filename": filename,
                "experiments": ";".join(families),
                "n": n,
                "m": m,
                "target_density": density,
                "actual_density": measured_density,
                "seed": seed,
                "min_subset_size": min(subset_sizes),
                "max_subset_size": max(subset_sizes),
                "mean_subset_size": sum(subset_sizes) / m,
                "empty_subsets": subset_sizes.count(0),
                "unique_subsets": len({
                    frozenset(subset)
                    for subset in instance["subsets"]
                }),
                "feasible": True,
            }

            # JSON does not support sets, so convert
            # sets to sorted lists before saving.
            data = {
                "metadata": info,
                "universe": sorted(instance["universe"]),
                "subsets": [
                    sorted(subset)
                    for subset in instance["subsets"]
                ],
            }

            with open(
                output_dir / filename,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(data, file)

            metadata.append(info)

            print(
                f"Generated {instance_id} | "
                f"Actual density: {measured_density:.4f}"
            )

    # Save a master table describing all datasets
    with open(
        output_dir / "manifest.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(metadata[0].keys())
        )

        writer.writeheader()
        writer.writerows(metadata)

    print("\nGeneration completed.")
    print(f"Unique configurations: {len(configurations)}")
    print(f"Total instances: {len(metadata)}")
    print(f"Saved to: {output_dir}")
