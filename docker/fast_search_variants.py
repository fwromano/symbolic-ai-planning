#!/usr/bin/env python3
"""
fast_search_variants.py
Multiple search algorithm variants optimized for finding sufficient solutions quickly.
Includes configurations for fastest search, lowest memory, and balanced approaches.
"""

import argparse, csv, os, re, subprocess, sys, time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Search configurations with different trade-offs
SEARCH_CONFIGS = {
    # Original optimal search for comparison
    'optimal': {
        'name': 'A* with LM-cut (Optimal)',
        'search': 'astar(lmcut())',
        'desc': 'Finds optimal solution but slowest'
    },
    
    # FASTEST SEARCHES (may use more memory)
    'greedy_ff': {
        'name': 'Greedy Best-First (FF heuristic)',
        'search': 'eager_greedy([ff()])',
        'desc': 'Very fast, reasonable quality, moderate memory'
    },
    'lazy_greedy_ff': {
        'name': 'Lazy Greedy (FF heuristic)',
        'search': 'lazy_greedy([ff()], preferred=[ff()])',
        'desc': 'Fastest search, good quality, higher memory'
    },
    'greedy_add': {
        'name': 'Greedy (Additive heuristic)',
        'search': 'eager_greedy([add()])',
        'desc': 'Fast with simple heuristic, lower quality'
    },
    
    # LOWEST MEMORY SEARCHES
    'lazy_wastar_low_mem': {
        'name': 'Lazy Weighted A* (W=2)',
        'search': 'lazy_wastar([ff()], w=2)',
        'desc': 'Low memory, good quality/speed balance'
    },
    'ehc': {
        'name': 'Enforced Hill-Climbing',
        'search': 'ehc([ff()])',
        'desc': 'Very low memory, fast on many domains'
    },
    
    # BALANCED MIDDLE GROUND OPTIONS
    'lazy_wastar_3': {
        'name': 'Lazy Weighted A* (W=3)',
        'search': 'lazy_wastar([ff()], w=3)',
        'desc': 'Good balance: 3x suboptimality bound'
    },
    'lazy_wastar_5': {
        'name': 'Lazy Weighted A* (W=5)',
        'search': 'lazy_wastar([ff()], w=5)',
        'desc': 'Faster with 5x suboptimality bound'
    },
    'eager_wastar': {
        'name': 'Eager Weighted A* (W=3)',
        'search': 'eager_wastar([ff()], w=3)',
        'desc': 'Eager evaluation, predictable memory'
    },
    'greedy_cg': {
        'name': 'Greedy (Causal Graph heuristic)',
        'search': 'eager_greedy([cg()])',
        'desc': 'Fast with structural heuristic'
    },
    
    # ANYTIME SEARCHES (find solution then improve)
    'iterated_wastar': {
        'name': 'Iterated Weighted A*',
        'search': 'iterated([lazy_wastar([ff()], w=5), lazy_wastar([ff()], w=3), lazy_wastar([ff()], w=2)])',
        'desc': 'Anytime: quickly finds solution then improves'
    },
    'restart_wastar': {
        'name': 'Restarting Weighted A*',
        'search': 'lazy_wastar([ff()], w=5, repeat_last=true)',
        'desc': 'Restarts with better bounds when found'
    }
}

DOWNWARD_PATH   = '/opt/downward/fast-downward.py'
MOUNT_INNER_DIR = '/data'

def _run(cmd, timeout=None):
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        dur = time.time() - t0
        if proc.returncode:
            # Don't fail hard - some searches might not find solutions
            # But let's see what the error is for debugging
            if "timeout" not in proc.stderr and dur < 2.0:  # Quick failure suggests config error
                print(f"\n    ERROR OUTPUT: {proc.stderr[:200]}")
            return proc.stdout + proc.stderr, dur, False
        return proc.stdout + proc.stderr, dur, True
    except subprocess.TimeoutExpired:
        dur = time.time() - t0
        return "Search timed out", dur, False

def run_docker(image, host_dir, domain, prob, search_config, timeout=300, memory_limit='8G'):
    """Run docker with timeout and memory limits
    
    Args:
        timeout: Time limit in seconds (default 300s = 5 minutes)
        memory_limit: Docker memory limit (default 8G)
    """
    # Use Python's subprocess timeout
    out, dur, success = _run([
        'docker','run','--rm',
        '-v',f'{host_dir}:{MOUNT_INNER_DIR}:ro',
        '--memory', memory_limit,
        '--memory-swap', memory_limit,  # Prevent using swap
        image, 
        DOWNWARD_PATH,
        f'{MOUNT_INNER_DIR}/{domain}',
        f'{MOUNT_INNER_DIR}/{prob}',
        '--search', search_config
    ], timeout=timeout)
    return out, dur, success

def exec_docker(container, domain, prob, search_config, timeout=300):
    """Execute in container with timeout"""
    out, dur, success = _run([
        'docker','exec', container,
        DOWNWARD_PATH, domain, prob, 
        '--search', search_config
    ], timeout=timeout)
    return out, dur, success

def first_int(pat, text):
    m = re.search(pat, text)
    return int(m.group(1)) if m else None

def extract_size(fname):
    m = re.search(r'(\d+)x\d+\.pddl$', fname)
    return int(m.group(1)) if m else None

def extract_memory(text):
    """Extract peak memory usage in MB"""
    m = re.search(r'Peak memory: (\d+) KB', text)
    if m:
        return int(m.group(1)) / 1024  # Convert to MB
    return None

def run_single_config(args, config_key, config, problems):
    """Run a single search configuration on all problems"""
    print(f"\n{'='*60}")
    print(f"Testing: {config['name']}")
    print(f"Search: {config['search']}")
    print(f"Description: {config['desc']}")
    print(f"{'='*60}")
    
    rows = []
    timeout = args.timeout if hasattr(args, 'timeout') else 60  # Default 60s timeout
    
    for fname in problems:
        size = extract_size(fname)
        if size is None:
            continue
            
        print(f"  Problem {fname}...", end='', flush=True)
        host_prob = os.path.join(args.problems_dir, fname)
        
        if args.docker_image:
            out, dur, success = run_docker(
                args.docker_image,
                args.mount,
                os.path.relpath(args.domain, args.mount),
                os.path.relpath(host_prob, args.mount),
                config['search'],
                timeout=timeout
            )
        else:
            out, dur, success = exec_docker(
                args.container,
                f'{MOUNT_INNER_DIR}/{os.path.basename(args.domain)}',
                f'{MOUNT_INNER_DIR}/{fname}',
                config['search'],
                timeout=timeout
            )
        
        plan = first_int(r'Plan length: (\d+)', out)
        nodes = first_int(r'Expanded (\d+) state', out)
        memory = extract_memory(out)
        
        # Check if it was a timeout
        timeout_occurred = "timed out" in out.lower() or dur >= timeout - 1
        
        rows.append({
            'config': config_key,
            'config_name': config['name'],
            'problem': fname,
            'size': size,
            'plan_length': plan,
            'nodes_expanded': nodes,
            'memory_mb': memory,
            'runtime_s': dur,
            'success': success,
            'timeout': timeout_occurred
        })
        
        if timeout_occurred:
            status = "⏱"
        elif success:
            status = "✓"
        else:
            status = "✗"
        print(f" {status} {dur:6.2f}s, nodes={nodes}, plan={plan}")
    
    return rows

def analyze_results(df):
    """Analyze and print summary statistics"""
    print("\n" + "="*80)
    print("SUMMARY ANALYSIS")
    print("="*80)
    
    # Group by configuration
    summary = []
    for config in df['config'].unique():
        config_df = df[df['config'] == config]
        successful = config_df[config_df['success']]
        
        summary.append({
            'Config': config,
            'Name': config_df.iloc[0]['config_name'],
            'Success Rate': f"{len(successful)}/{len(config_df)} ({100*len(successful)/len(config_df):.0f}%)",
            'Avg Runtime (s)': f"{successful['runtime_s'].mean():.2f}",
            'Avg Memory (MB)': f"{successful['memory_mb'].mean():.1f}" if successful['memory_mb'].notna().any() else "N/A",
            'Avg Plan Length': f"{successful['plan_length'].mean():.0f}" if len(successful) > 0 else "N/A",
            'Avg Nodes': f"{successful['nodes_expanded'].mean():.0f}" if len(successful) > 0 else "N/A"
        })
    
    summary_df = pd.DataFrame(summary)
    print(summary_df.to_string(index=False))
    
    # Find best configurations
    successful_df = df[df['success']]
    if not successful_df.empty:
        print("\n" + "-"*60)
        print("RECOMMENDATIONS:")
        print("-"*60)
        
        # Fastest
        fastest = successful_df.groupby('config')['runtime_s'].mean().idxmin()
        print(f"🚀 Fastest: {SEARCH_CONFIGS[fastest]['name']}")
        print(f"   Average runtime: {successful_df[successful_df['config']==fastest]['runtime_s'].mean():.2f}s")
        
        # Lowest memory (if data available)
        if successful_df['memory_mb'].notna().any():
            mem_df = successful_df[successful_df['memory_mb'].notna()]
            if not mem_df.empty:
                lowest_mem = mem_df.groupby('config')['memory_mb'].mean().idxmin()
                print(f"\n💾 Lowest Memory: {SEARCH_CONFIGS[lowest_mem]['name']}")
                print(f"   Average memory: {mem_df[mem_df['config']==lowest_mem]['memory_mb'].mean():.1f} MB")
        
        # Best quality
        best_quality = successful_df.groupby('config')['plan_length'].mean().idxmin()
        print(f"\n⭐ Best Quality: {SEARCH_CONFIGS[best_quality]['name']}")
        print(f"   Average plan length: {successful_df[successful_df['config']==best_quality]['plan_length'].mean():.0f}")
        
        # Best balanced (scoring function)
        # Normalize metrics for scoring
        config_scores = []
        for config in successful_df['config'].unique():
            cfg_df = successful_df[successful_df['config'] == config]
            runtime_score = 1 - (cfg_df['runtime_s'].mean() / successful_df['runtime_s'].max())
            quality_score = 1 - (cfg_df['plan_length'].mean() / successful_df['plan_length'].max())
            success_score = len(cfg_df) / len(df[df['config'] == config])
            
            # Weighted score
            total_score = 0.4 * runtime_score + 0.3 * quality_score + 0.3 * success_score
            config_scores.append((config, total_score))
        
        best_balanced = max(config_scores, key=lambda x: x[1])[0]
        print(f"\n⚖️  Best Balanced: {SEARCH_CONFIGS[best_balanced]['name']}")
        print(f"   Good trade-off between speed, quality, and reliability")

def create_comparison_plots(df, output_prefix):
    """Create comparison plots for different metrics"""
    successful_df = df[df['success']]
    
    if successful_df.empty:
        print("No successful runs to plot!")
        return
    
    # 1. Runtime comparison
    plt.figure(figsize=(12, 8))
    for config in successful_df['config'].unique():
        config_df = successful_df[successful_df['config'] == config]
        config_df = config_df.sort_values('size')
        plt.plot(config_df['size'], config_df['runtime_s'], 
                'o-', label=SEARCH_CONFIGS[config]['name'][:30])
    
    plt.xscale('log', base=2)
    plt.yscale('log', base=2)
    plt.xlabel('Grid size n (n×n)')
    plt.ylabel('Runtime (s)')
    plt.title('Runtime Comparison: Different Search Strategies')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_runtime_comparison.png', dpi=150)
    print(f"Saved {output_prefix}_runtime_comparison.png")
    
    # 2. Quality comparison (plan length)
    plt.figure(figsize=(12, 8))
    for config in successful_df['config'].unique():
        config_df = successful_df[successful_df['config'] == config]
        config_df = config_df.sort_values('size')
        plt.plot(config_df['size'], config_df['plan_length'], 
                'o-', label=SEARCH_CONFIGS[config]['name'][:30])
    
    plt.xlabel('Grid size n (n×n)')
    plt.ylabel('Plan Length')
    plt.title('Solution Quality Comparison: Different Search Strategies')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_quality_comparison.png', dpi=150)
    print(f"Saved {output_prefix}_quality_comparison.png")
    
    # 3. Memory usage (if available)
    mem_df = successful_df[successful_df['memory_mb'].notna()]
    if not mem_df.empty:
        plt.figure(figsize=(12, 8))
        for config in mem_df['config'].unique():
            config_df = mem_df[mem_df['config'] == config]
            config_df = config_df.sort_values('size')
            plt.plot(config_df['size'], config_df['memory_mb'], 
                    'o-', label=SEARCH_CONFIGS[config]['name'][:30])
        
        plt.xlabel('Grid size n (n×n)')
        plt.ylabel('Memory Usage (MB)')
        plt.title('Memory Usage Comparison: Different Search Strategies')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_prefix}_memory_comparison.png', dpi=150)
        print(f"Saved {output_prefix}_memory_comparison.png")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('domain', help='explorationDomain.pddl')
    ap.add_argument('problems_dir', help='directory with exp-*/explore-* .pddl')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--docker-image', 
                    help='Docker image name (e.g., aibasel/downward, docker-downward)')
    mode.add_argument('--container')
    ap.add_argument('--mount', default=os.getcwd(),
                    help='host dir mounted at /data when using --docker-image')
    ap.add_argument('--out', default='fast_search_comparison.csv')
    ap.add_argument('--configs', nargs='+', 
                    choices=list(SEARCH_CONFIGS.keys()),
                    help='Specific configs to test (default: all)')
    ap.add_argument('--quick', action='store_true',
                    help='Quick test with just fast/balanced/low-mem options')
    ap.add_argument('--timeout', type=int, default=60,
                    help='Timeout per problem in seconds (default: 60)')
    args = ap.parse_args()
    
    # Select configurations to test
    if args.configs:
        configs_to_test = {k: SEARCH_CONFIGS[k] for k in args.configs}
    elif args.quick:
        # Quick mode: test representative algorithms
        configs_to_test = {
            'lazy_greedy_ff': SEARCH_CONFIGS['lazy_greedy_ff'],      # Fastest
            'lazy_wastar_low_mem': SEARCH_CONFIGS['lazy_wastar_low_mem'],  # Low memory
            'lazy_wastar_3': SEARCH_CONFIGS['lazy_wastar_3'],        # Balanced
            'optimal': SEARCH_CONFIGS['optimal']                      # Baseline
        }
    else:
        configs_to_test = SEARCH_CONFIGS
    
    print("Fast Search Variants Analysis")
    print(f"Testing {len(configs_to_test)} search configurations...")
    
    # Get problem files
    problems = sorted([f for f in os.listdir(args.problems_dir) 
                      if extract_size(f) is not None])
    
    if not problems:
        print("No matching problems found!", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(problems)} problems to test")
    
    # Run all configurations
    all_rows = []
    for config_key, config in configs_to_test.items():
        rows = run_single_config(args, config_key, config, problems)
        all_rows.extend(rows)
    
    # Save results
    df = pd.DataFrame(all_rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote detailed results to {args.out}")
    
    # Analyze and summarize
    analyze_results(df)
    
    # Create plots
    create_comparison_plots(df, args.out.replace('.csv', ''))

if __name__ == '__main__':
    main()