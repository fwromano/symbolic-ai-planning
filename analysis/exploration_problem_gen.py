#!/usr/bin/env python3
"""
exploration_problem_gen.py
Generate solvable exploration-grid PDDL problems.

We ensure that **every** location l has at least one robot r
such that (can-traverse r l) AND (can-observe r l).

Distribution rules (per grid):
    * ~10 % locations have HIGH traverse cost (=5) for both robots.
    * ~10 % locations are traversable by only ONE robot.
    * ~10 % locations are observable by only ONE robot.
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
ROBOTS      = ["B", "G"]
HIGH_COST   = 5
EASY_COST   = 1

def cell_name(r, c):
    return f"l{r}{c}"

def grid_cells(n):
    return [cell_name(r, c) for r in range(1, n+1) for c in range(1, n+1)]

def adjacency_pairs(n):
    pairs = []
    for r in range(1, n+1):
        for c in range(1, n+1):
            here = cell_name(r, c)
            if r < n: pairs.append((here, cell_name(r+1, c)))
            if c < n: pairs.append((here, cell_name(r, c+1)))
    # make bidirectional
    return pairs + [(b,a) for (a,b) in pairs]

def rng(pool, k):
    return random.sample(pool, k) if k > 0 else []

def problem_text(n, seed):
    random.seed(seed)
    cells = grid_cells(n)

    # 10% high-cost
    k = math.ceil(len(cells)/10)
    hard   = set(rng(cells, k))

    # 10% solo-traverse
    rem    = [l for l in cells if l not in hard]
    solo_trav = set(rng(rem, k))

    # 10% solo-observe
    rem2   = [l for l in rem if l not in solo_trav]
    solo_obs  = set(rng(rem2, k))

    # build initial capability maps
    trav = { (r,l): True for r in ROBOTS for l in cells }
    obs  = { (r,l): True for r in ROBOTS for l in cells }

    # apply solo-traverse
    for l in solo_trav:
        # pick which robot keeps traverse
        keeper = random.choice(ROBOTS)
        for r in ROBOTS:
            trav[(r,l)] = (r == keeper)

    # apply solo-observe
    for l in solo_obs:
        keeper = random.choice(ROBOTS)
        for r in ROBOTS:
            obs[(r,l)] = (r == keeper)

    # enforce coupling: each cell must have some r with both trav & obs
    for l in cells:
        if not any(trav[(r,l)] and obs[(r,l)] for r in ROBOTS):
            # randomly grant both rights to one robot
            r = random.choice(ROBOTS)
            trav[(r,l)] = True
            obs[(r,l)]  = True

    # now render PDDL ---------------------------------------------------
    obj_line = " ".join(ROBOTS) + " - robot\n        " + \
               " ".join(cells) + " - location"

    init_atoms = []
    # start positions
    init_atoms += [f"(at B l11)", f"(at G l11)"]

    # adjacency
    for a,b in adjacency_pairs(n):
        init_atoms.append(f"(adjacent {a} {b})")

    # capabilities
    for l in cells:
        for r in ROBOTS:
            if trav[(r,l)]:
                init_atoms.append(f"(can-traverse {r} {l})")
            if obs[(r,l)]:
                init_atoms.append(f"(can-observe {r} {l})")

    # costs
    for l in cells:
        cost = HIGH_COST if l in hard else EASY_COST
        for r in ROBOTS:
            init_atoms.append(f"(= (traverse-cost {r} {l}) {cost})")
    init_atoms.append("(= (total-cost) 0)")

    # goal: explore all cells + both robots at bottom-right
    last = cell_name(n,n)
    goal_atoms = [f"(explored {l})" for l in cells] + [f"(at B {last})", f"(at G {last})"]

    # pretty-print blocks
    def block(atoms, indent=8):
        return "\n" + " "*indent + "\n".join(atoms)

    return f"""(define (problem exp-{n}x{n})
    (:domain {DOMAIN_NAME})

    (:objects{block([obj_line],8)})
    (:init{block(init_atoms,8)})
    (:goal (and{block(goal_atoms,8)}))
    (:metric minimize (total-cost))
)"""

def sizes_from_args(args):
    if args.size:
        return [args.size]
    return list(range(args.range[0], args.range[1]+1))

def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--size",  type=int, nargs="?", help="single grid size")
    grp.add_argument("--range", nargs=2, type=int, metavar=("MIN","MAX"))
    ap.add_argument("--outdir", default=".", help="output directory")
    ap.add_argument("--seed",   type=int, default=0, help="random seed")
    args = ap.parse_args()

    pathlib.Path(args.outdir).mkdir(exist_ok=True, parents=True)
    for n in sizes_from_args(args):
        text = problem_text(n, seed=args.seed + n)
        path = os.path.join(args.outdir, f"exp-{n}x{n}.pddl")
        with open(path,"w") as f:
            f.write(text)
        print(f"Wrote {path}")

if __name__=="__main__":
    main()


