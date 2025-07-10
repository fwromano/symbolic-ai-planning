#!/usr/bin/env python3
"""
exploration_complexity_analysis.py
Profile grid problems (exp-NxN.pddl or explore-NxN.pddl) with Fast-Downward in Docker.
Uses Lazy Weighted A* (W=3) for complete but faster search.
"""
import argparse, csv, os, re, subprocess, sys, time
import matplotlib.pyplot as plt
import pandas as pd

# Changed from optimal to complete satisficing search
SEARCH_OPT      = 'lazy_wastar([ff()], w=3)'
DOWNWARD_PATH   = '/opt/downward/fast-downward.py'
MOUNT_INNER_DIR = '/data'


def _run(cmd, timeout=300):
    """Run command with timeout support"""
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        dur = time.time() - t0
        if proc.returncode:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            raise RuntimeError(f"Command failed: {' '.join(cmd)}")
        return proc.stdout + proc.stderr, dur, False  # False = not timeout
    except subprocess.TimeoutExpired:
        dur = time.time() - t0
        print(f"Search timed out after {timeout}s")
        return "", dur, True  # True = timeout occurred


def run_docker(image, host_dir, domain, prob, timeout=300):
    out, dur, timed_out = _run([
        'docker','run','--rm',
        '-v',f'{host_dir}:{MOUNT_INNER_DIR}:ro',
        '--memory', '8G',
        '--memory-swap', '8G',
        image, DOWNWARD_PATH,
        f'{MOUNT_INNER_DIR}/{domain}',
        f'{MOUNT_INNER_DIR}/{prob}',
        '--search', SEARCH_OPT
    ], timeout=timeout)
    return out, dur, timed_out


def exec_docker(container, domain, prob, timeout=300):
    out, dur, timed_out = _run([
        'docker','exec',container,
        DOWNWARD_PATH, domain, prob, '--search', SEARCH_OPT
    ], timeout=timeout)
    return out, dur, timed_out


def first_int(pat, text):
    m = re.search(pat, text)
    return int(m.group(1)) if m else None


def extract_size(fname):
    # match '...-NxM.pddl' and take N
    m = re.search(r'(\d+)x\d+\.pddl$', fname)
    return int(m.group(1)) if m else None


def extract_memory(text):
    """Extract peak memory usage in MB"""
    m = re.search(r'Peak memory: (\d+) KB', text)
    if m:
        return int(m.group(1)) / 1024  # Convert to MB
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('domain', help='explorationDomain.pddl')
    ap.add_argument('problems_dir', help='directory with exp-*/explore-* .pddl')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--docker-image')
    mode.add_argument('--container')
    ap.add_argument('--mount', default=os.getcwd(),
                    help='host dir mounted at /data when using --docker-image')
    ap.add_argument('--timeout', type=int, default=300,
                    help='timeout per problem in seconds (default: 300)')
    ap.add_argument('--out', default='explore_metrics_wastar3.csv')
    args = ap.parse_args()
    
    print(f"Starting analysis with Lazy W-A* (W=3)...")
    print(f"Timeout: {args.timeout}s per problem")
    
    rows = []
    problems = sorted([f for f in os.listdir(args.problems_dir) if extract_size(f) is not None])
    print(f"Found {len(problems)} problems to analyze")
    
    for fname in problems:
        size = extract_size(fname)
        if size is None:
            continue
            
        print(f"\nAnalyzing {fname} (size {size}x{size})...", end='', flush=True)
        host_prob = os.path.join(args.problems_dir, fname)
        
        if args.docker_image:
            out, dur, timed_out = run_docker(
                args.docker_image,
                args.mount,
                os.path.relpath(args.domain, args.mount),
                os.path.relpath(host_prob, args.mount),
                timeout=args.timeout
            )
        else:
            out, dur, timed_out = exec_docker(
                args.container,
                f'{MOUNT_INNER_DIR}/{os.path.basename(args.domain)}',
                f'{MOUNT_INNER_DIR}/{fname}',
                timeout=args.timeout
            )
        
        if timed_out:
            print(f" TIMEOUT after {dur:.2f}s")
            rows.append({
                'problem': fname,
                'size': size,
                'plan_length': None,
                'nodes_expanded': None,
                'memory_mb': None,
                'runtime_s': dur,
                'timeout': True
            })
        else:
            plan = first_int(r'Plan length: (\d+)', out)
            nodes = first_int(r'Expanded (\d+) state', out)
            memory = extract_memory(out)
            
            print(f" SUCCESS in {dur:.2f}s (plan_len={plan}, nodes={nodes})")
            
            rows.append({
                'problem': fname,
                'size': size,
                'plan_length': plan,
                'nodes_expanded': nodes,
                'memory_mb': memory,
                'runtime_s': dur,
                'timeout': False
            })

    if not rows:
        print("No matching problems found!", file=sys.stderr)
        sys.exit(1)

    # save CSV
    df = pd.DataFrame(rows).sort_values('size')
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}")
    
    # Summary statistics
    successful = df[~df['timeout']]
    if len(successful) > 0:
        print(f"\nSummary:")
        print(f"  Problems solved: {len(successful)}/{len(df)}")
        print(f"  Average runtime: {successful['runtime_s'].mean():.2f}s")
        print(f"  Max runtime: {successful['runtime_s'].max():.2f}s")
        if successful['plan_length'].notna().any():
            print(f"  Average plan length: {successful['plan_length'].mean():.1f}")

    # plot runtime
    plt.figure(figsize=(10, 6))
    
    # Plot successful runs
    success_df = df[~df['timeout']].copy()
    if len(success_df) > 0:
        success_df = success_df.sort_values('size')
        plt.plot(success_df['size'], success_df['runtime_s'], 'o-', label='Solved', markersize=8)
    
    # Mark timeouts
    timeout_df = df[df['timeout']].copy()
    if len(timeout_df) > 0:
        plt.plot(timeout_df['size'], timeout_df['runtime_s'], 'rx', label='Timeout', markersize=10)
    
    plt.xscale('log', base=2)
    plt.yscale('log', base=2)
    plt.xlabel('Grid size n (n×n)')
    plt.ylabel('Runtime (s)')
    plt.title('Exploration with Lazy W-A* (W=3): Runtime vs. Grid Size')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig('explore_runtime_vs_size_wastar3.png')
    print(f"Saved explore_runtime_vs_size_wastar3.png")
    
    # plot nodes expanded if available
    if success_df['nodes_expanded'].notna().any():
        plt.figure(figsize=(10, 6))
        success_df_nodes = success_df[success_df['nodes_expanded'].notna()].sort_values('size')
        plt.plot(success_df_nodes['size'], success_df_nodes['nodes_expanded'], 'o-', markersize=8)
        plt.xscale('log', base=2)
        plt.yscale('log', base=10)
        plt.xlabel('Grid size n (n×n)')
        plt.ylabel('Nodes Expanded')
        plt.title('Exploration with Lazy W-A* (W=3): Search Effort vs. Grid Size')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('explore_nodes_vs_size_wastar3.png')
        print(f"Saved explore_nodes_vs_size_wastar3.png")


if __name__ == '__main__':
    main()