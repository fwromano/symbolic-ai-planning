#!/usr/bin/env python3
"""
road_problem_gen.py
Generate ROAD domain PDDL problem files.

Usage examples
--------------
# one file with 20 segments
python road_problem_gen.py --segments 20 --outdir ./problems

# powers of two between 1 and 10000 (inclusive)
python road_problem_gen.py --range 1 10000 --distribution log2 --outdir ./problems
"""
import argparse, math, os, pathlib

DOMAIN_NAME = "road"
VEHICLES     = "v1 - vehicle\n        v2 - bulldozer"

def locations(n_segs: int) -> list[str]:
    """Return list ['l1', 'l2', …, 'l{n_segs+1}']"""
    return [f"l{i}" for i in range(1, n_segs + 2)]

def adjacency_pairs(locs: list[str]) -> list[tuple[str, str]]:
    """Bidirectional edges along the chain"""
    return [(locs[i], locs[i + 1]) for i in range(len(locs) - 1)]

def problem_text(n_segs: int) -> str:
    """Construct a ROAD‑chain problem with n_segs segments."""
    locs  = locations(n_segs)
    edges = adjacency_pairs(locs)

    objs  = f"{VEHICLES}\n        " + " ".join(locs) + " - location"
    init_lines = [
        "(at v1 l1)",
        "(at v2 l1)",
        "(rubble l2)",                   # first obstacle
    ] + [f"(adjacent {a} {b})\n        (adjacent {b} {a})" for a, b in edges]

    init  = "\n        ".join(init_lines)
    goal  = f"(at v1 {locs[-1]})"

    return f"""(define (problem road-{n_segs})
    (:domain {DOMAIN_NAME})
    (:objects
        {objs}
    )
    (:init
        {init}
    )
    (:goal {goal})
)"""

def segment_sizes(args) -> list[int]:
    if args.segments:
        return [args.segments]
    lo, hi = args.range
    if args.distribution == "log2":
        k_max = int(math.log2(hi))
        return [2 ** k for k in range(int(math.log2(max(lo,1))), k_max + 1) if lo <= 2 ** k <= hi]
    # linear
    step = args.step or 1
    return list(range(lo, hi + 1, step))

def main():
    ap = argparse.ArgumentParser()
    g  = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--segments", type=int, help="exact number of segments")
    g.add_argument("--range",    nargs=2, type=int, metavar=("MIN", "MAX"),
                   help="generate many problems between MIN and MAX segments")
    ap.add_argument("--distribution", choices=("linear", "log2"), default="linear",
                    help="size selection pattern for --range (default linear)")
    ap.add_argument("--step", type=int, help="step when using linear distribution")
    ap.add_argument("--outdir", default=".", help="directory for output *.pddl files")
    args = ap.parse_args()

    sizes = segment_sizes(args)
    pathlib.Path(args.outdir).mkdir(parents=True, exist_ok=True)
    for n in sizes:
        text = problem_text(n)
        path = os.path.join(args.outdir, f"road-{n}.pddl")
        with open(path, "w") as f:
            f.write(text)
        print(f"Wrote {path}")

if __name__ == "__main__":
    main()
