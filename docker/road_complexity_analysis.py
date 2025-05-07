#!/usr/bin/env python3
"""
road_complexity_analysis.py
Profile ROAD problems while keeping Fast‑Downward inside Docker.

Two usage modes
---------------
1. docker run  (stateless: a fresh container per problem)
   python road_complexity_analysis.py DOMAIN PROBLEMS_DIR \
       --docker-image planner:latest --mount $(pwd)

2. docker exec (reuse an already‑running container that has the host
   directory mounted at /data)
   python road_complexity_analysis.py DOMAIN PROBLEMS_DIR \
       --container planner_container
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------------------
SEARCH_OPT      = 'astar(add())'
DOWNWARD_PATH   = '/opt/downward/fast-downward.py'   # inside container
MOUNT_INNER_DIR = '/data'                            # host dir is mounted here
# ---------------------------------------------------------------------


# ---------- Docker interaction ---------------------------------------
def _run(cmd: list[str]) -> tuple[str, float]:
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.time() - start
    if proc.returncode:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise RuntimeError(f"command failed: {' '.join(cmd)}")
    return proc.stdout + proc.stderr, dur


def run_docker(image: str, host_dir: str, domain: str, problem: str) -> tuple[str, float]:
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{host_dir}:{MOUNT_INNER_DIR}:ro",
        image,
        DOWNWARD_PATH,
        f"{MOUNT_INNER_DIR}/{domain}",
        f"{MOUNT_INNER_DIR}/{problem}",
        "--search", SEARCH_OPT,
    ]
    return _run(cmd)


def exec_docker(container: str, domain: str, problem: str) -> tuple[str, float]:
    cmd = [
        "docker", "exec", container,
        DOWNWARD_PATH,
        domain,     
        problem,
        "--search", SEARCH_OPT,
    ]
    return _run(cmd)



# ---------- Parsing helpers ------------------------------------------
def first_int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def segments_from_name(fname: str) -> int | None:
    m = re.search(r"road-(\d+)\.pddl", fname)
    return int(m.group(1)) if m else None


# ---------- Main -----------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", help="roadDomain.pddl (host path)")
    ap.add_argument("problems_dir", help="Directory with road-*.pddl")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--docker-image", help="Image name for docker run")
    mode.add_argument("--container", help="Container name for docker exec")
    ap.add_argument("--mount", default=os.getcwd(),
                    help="Host directory mounted at /data when using --docker-image")
    ap.add_argument("--out", default="road_metrics.csv", help="CSV output file")
    args = ap.parse_args()

    rows = []
    for fname in sorted(os.listdir(args.problems_dir)):
        if not fname.startswith("road-") or not fname.endswith(".pddl"):
            continue

        host_problem = os.path.join(args.problems_dir, fname)
        if args.docker_image:
            out, dur = run_docker(
                args.docker_image,
                args.mount,
                os.path.relpath(args.domain, args.mount),
                os.path.relpath(host_problem, args.mount),
            )
        else:
            out, dur = exec_docker(
                args.container,
                os.path.join(MOUNT_INNER_DIR, os.path.basename(args.domain)),
                os.path.join(MOUNT_INNER_DIR, fname),
            )

        plan_len = first_int(r"Plan length: (\d+)", out)
        nodes    = first_int(r"Expanded (\d+) state", out)
        segs     = segments_from_name(fname)

        rows.append(dict(
            problem=fname, segments=segs,
            plan_length=plan_len, nodes_expanded=nodes,
            runtime_s=dur,
        ))
        print(f"{fname:<15} {dur:6.3f}s  nodes={nodes}")

    # save CSV
    with open(args.out, "w", newline="") as f:
        csv.DictWriter(f, rows[0].keys()).writeheader()
        csv.DictWriter(f, rows[0].keys()).writerows(rows)
    print(f"Wrote {args.out}")

    # runtime plot
    df = pd.DataFrame(rows).sort_values("segments")
    plt.figure()
    plt.plot(df.segments, df.runtime_s, marker="o")
    plt.xscale("log", base=2)
    plt.yscale("log", base=2)
    plt.xlabel("Segments")
    plt.ylabel("Runtime (s)")
    plt.title("Empirical Runtime vs. Problem Size")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("runtime_vs_size.png")
    print("Saved runtime_vs_size.png")


if __name__ == "__main__":
    main()
