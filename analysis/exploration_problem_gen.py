#!/usr/bin/env python3
"""
exploration_problem_gen.py
Generate grid‑style PDDL problems for the 'exploration' domain.

Distribution rules (per grid):
    * ~10 % locations have HIGH traverse cost (=5) for both robots.
    * ~10 % locations are traversable by only ONE robot.
    * ~10 % locations are observable by only ONE robot.
All other cells are easy (cost 1), traversable, and observable by both.

Usage examples
--------------
# single 4×4 grid
python exploration_problem_gen.py --size 4 --outdir problems

# batches: 3×3 up to 25×25
python exploration_problem_gen.py --range 3 25 --outdir problems
"""
import argparse, math, os, pathlib, random
from itertools import product

DOMAIN_NAME = "exploration"
ROBOTS      = ["B", "G"]            # two robots, names fixed
HIGH_COST   = 5
EASY_COST   = 1

def rng(shuffle_pool, k):
    """Return k items sampled without replacement (k may be 0)."""
    return random.sample(shuffle_pool, k) if k else []

# ---------------------------------------------------------------------
def cell_name(x, y):
    return f"l{x}{y}"          # e.g. l23 is row2‑col3 (1‑based)

def grid_locations(n):
    return [cell_name(r, c) for r in range(1, n+1) for c in range(1, n+1)]

def adjacency_pairs(n):
    """4‑connected neighbours for n×n grid."""
    pairs = []
    for r in range(1, n+1):
        for c in range(1, n+1):
            if r < n:  pairs.append((cell_name(r, c), cell_name(r+1, c)))
            if c < n:  pairs.append((cell_name(r, c), cell_name(r, c+1)))
    return pairs + [(b, a) for (a, b) in pairs]   # make bidirectional

# ---------------------------------------------------------------------
def problem_text(n, seed):
    random.seed(seed)
    locs = grid_locations(n)
    # choose special‑case sets
    k_hard  = math.ceil(len(locs) / 10)            # 10 %
    hard_cells  = rng(locs, k_hard)

    remaining = [l for l in locs if l not in hard_cells]
    k_untrv   = math.ceil(len(locs) / 10)
    untrv_cells = rng(remaining, k_untrv)

    remaining = [l for l in remaining if l not in untrv_cells]
    k_unobs   = math.ceil(len(locs) / 10)
    unobs_cells = rng(remaining, k_unobs)

    # Build PDDL sections ------------------------------------------------
    obj_line = " ".join(ROBOTS) + " - robot\n        " + " ".join(locs) + " - location"

    init = []

    # start positions: both at top‑left
    init += [f"(at B {cell_name(1,1)})", f"(at G {cell_name(1,1)})"]

    # adjacency
    init += [f"(adjacent {a} {b})" for (a,b) in adjacency_pairs(n)]

    # traversability
    for l in locs:
        if l in untrv_cells:
            # only one robot (pick B if even hash, else G)
            chosen = "B" if hash(l) % 2 == 0 else "G"
            init.append(f"(can-traverse {chosen} {l})")
        else:
            for rob in ROBOTS:
                init.append(f"(can-traverse {rob} {l})")

    # observation
    for l in locs:
        if l in unobs_cells:
            chosen = "B" if hash(l) % 2 else "G"
            init.append(f"(can-observe {chosen} {l})")
        else:
            for rob in ROBOTS:
                init.append(f"(can-observe {rob} {l})")

    # traverse‑cost
    for l in locs:
        cost = HIGH_COST if l in hard_cells else EASY_COST
        for rob in ROBOTS:
            init.append(f"(= (traverse-cost {rob} {l}) {cost})")
    init.append("(= (total-cost) 0)")

    # goal: all cells explored + both robots at bottom‑right
    last = cell_name(n, n)
    goal_atoms = [f"(explored {l})" for l in locs] + [f"(at B {last})", f"(at G {last})"]

    return f"""(define (problem exp-{n}x{n})
    (:domain {DOMAIN_NAME})

    (:objects
        {obj_line}
    )

    (:init
        {' '.join(init)}
    )

    (:goal (and
        {' '.join(goal_atoms)}
    ))

    (:metric minimize (total-cost))
)"""

# ---------------------------------------------------------------------
def sizes_from_args(args):
    if args.size:
        return [args.size]
    lo, hi = args.range
    return list(range(lo, hi+1))

def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--size", type=int, help="one grid size (e.g. 4)")
    grp.add_argument("--range", nargs=2, type=int, metavar=("MIN", "MAX"),
                     help="generate every square size in [MIN..MAX]")
    ap.add_argument("--outdir", default=".", help="directory for *.pddl output")
    ap.add_argument("--seed", type=int, default=0, help="random seed (default 0)")
    args = ap.parse_args()

    pathlib.Path(args.outdir).mkdir(parents=True, exist_ok=True)
    for n in sizes_from_args(args):
        text = problem_text(n, seed=args.seed + n)
        path = os.path.join(args.outdir, f"explore-{n}x{n}.pddl")
        with open(path, "w") as f:
            f.write(text)
        print(f"Wrote {path}")

if __name__ == "__main__":
    main()
