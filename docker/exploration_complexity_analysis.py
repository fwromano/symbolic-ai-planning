#!/usr/bin/env python3
"""
exploration_complexity_analysis.py
Profile grid problems (exp-NxN.pddl or explore-NxN.pddl) with Fast-Downward in Docker.
"""
import argparse, csv, os, re, subprocess, sys, time
import matplotlib.pyplot as plt
import pandas as pd

SEARCH_OPT      = 'astar(lmcut())'
DOWNWARD_PATH   = '/opt/downward/fast-downward.py'
MOUNT_INNER_DIR = '/data'


def _run(cmd):
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.time() - t0
    if proc.returncode:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc.stdout + proc.stderr, dur


def run_docker(image, host_dir, domain, prob):
    return _run([
        'docker','run','--rm',
        '-v',f'{host_dir}:{MOUNT_INNER_DIR}:ro',
        image, DOWNWARD_PATH,
        f'{MOUNT_INNER_DIR}/{domain}',
        f'{MOUNT_INNER_DIR}/{prob}',
        '--search', SEARCH_OPT
    ])


def exec_docker(container, domain, prob):
    return _run([
        'docker','exec',container,
        DOWNWARD_PATH, domain, prob, '--search', SEARCH_OPT
    ])


def first_int(pat, text):
    m = re.search(pat, text)
    return int(m.group(1)) if m else None


def extract_size(fname):
    # match '...-NxM.pddl' and take N
    m = re.search(r'(\d+)x\d+\.pddl$', fname)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('domain', help='explorationDomain.pddl')
    ap.add_argument('problems_dir', help='directory with exp-*/explore-* .pddl')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--docker-image')
    mode.add_argument('--container')
    ap.add_argument('--mount', default=os.getcwd(),
                    help='host dir mounted at /data when using --docker-image')
    ap.add_argument('--out', default='explore_metrics.csv')
    args = ap.parse_args()
    print("Starting analysis...")
    rows = []
    print(sorted(os.listdir(args.problems_dir)))
    for fname in sorted(os.listdir(args.problems_dir)):
        size = extract_size(fname)
        print(f"Analying {size}!")
        if size is None:
            continue
        host_prob = os.path.join(args.problems_dir, fname)
        if args.docker_image:
            out, dur = run_docker(
                args.docker_image,
                args.mount,
                os.path.relpath(args.domain, args.mount),
                os.path.relpath(host_prob, args.mount)
            )
        else:
            out, dur = exec_docker(
                args.container,
                f'{MOUNT_INNER_DIR}/{os.path.basename(args.domain)}',
                f'{MOUNT_INNER_DIR}/{fname}'
            )
        plan = first_int(r'Plan length: (\d+)', out)
        nodes= first_int(r'Expanded (\d+) state', out)

        rows.append({
            'problem': fname,
            'size': size,
            'plan_length': plan,
            'nodes_expanded': nodes,
            'runtime_s': dur
        })
        print(f'{fname:20s}  {dur:6.2f}s  nodes={nodes}')

    if not rows:
        print("No matching problems found!", file=sys.stderr)
        sys.exit(1)

    # save CSV
    df = pd.DataFrame(rows).sort_values('size')
    df.to_csv(args.out, index=False)
    print("Wrote", args.out)

    # plot
    plt.figure()
    plt.plot(df.size, df.runtime_s, 'o-')
    plt.xscale('log', base=2); plt.yscale('log', base=2)
    plt.xlabel('Grid size n (n×n)')
    plt.ylabel('Runtime (s)')
    plt.title('Exploration: Runtime vs. Grid Size')
    plt.grid(True); plt.tight_layout()
    plt.savefig('explore_runtime_vs_size.png')
    print("Saved explore_runtime_vs_size.png")


if __name__ == '__main__':
    main()
