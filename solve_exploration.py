#!/usr/bin/env python3
"""
All-in-one script: Config → PDDL → Solution
Handles Docker container management automatically
"""

import yaml
import subprocess
import os
import sys
import time

def check_docker():
    """Check if Docker is available"""
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        return True
    except:
        return False

def container_exists(name):
    """Check if a container with given name exists"""
    result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}'], 
                          capture_output=True, text=True)
    return name in result.stdout.split('\n')

def container_running(name):
    """Check if a container is running"""
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                          capture_output=True, text=True)
    return name in result.stdout.split('\n')

def setup_docker_container():
    """Setup the Fast Downward Docker container"""
    print("Setting up Docker container...")
    
    # Check if we need to build
    if os.path.exists('docker/compose.yaml'):
        print("Building Docker image...")
        subprocess.run(['docker', 'compose', '-f', 'compose.yaml', 'build'], 
                      cwd='docker', check=True)
    
    # Check container status
    if container_exists('fast-downward'):
        if container_running('fast-downward'):
            print("Container 'fast-downward' is already running")
            return True
        else:
            print("Removing stopped container...")
            subprocess.run(['docker', 'rm', 'fast-downward'], check=True)
    
    # Start container
    print("Starting container...")
    try:
        # Try direct docker run
        subprocess.run([
            'docker', 'run', '-d', '--name', 'fast-downward',
            '-v', f'{os.getcwd()}:/workspace',
            '-w', '/workspace',
            'fast-downward',
            'sleep', 'infinity'
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start container: {e}")
        return False
    
    # Give container time to start
    time.sleep(2)
    return True

def solve_with_docker(domain_file, problem_file, search_algorithm="astar(add())"):
    """Solve using Docker container"""
    print(f"\nSolving {problem_file} with {search_algorithm}...")
    
    # Ensure container is running
    if not container_running('fast-downward'):
        setup_docker_container()
    
    # Copy files to container if needed
    subprocess.run(['docker', 'cp', domain_file, f'fast-downward:/workspace/{domain_file}'])
    subprocess.run(['docker', 'cp', problem_file, f'fast-downward:/workspace/{problem_file}'])
    
    # Run the planner
    cmd = [
        'docker', 'exec', 'fast-downward',
        '/opt/downward/fast-downward.py',
        f'/workspace/{domain_file}',
        f'/workspace/{problem_file}',
        '--search', search_algorithm
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse and display results
    if result.returncode == 0:
        output = result.stdout
        lines = output.split('\n')
        
        # Look for the plan
        plan_started = False
        plan_steps = []
        total_cost = None
        solution_found = False
        
        for i, line in enumerate(lines):
            # Fast Downward outputs the plan after "Solution found!"
            if 'Solution found!' in line or 'Solution found.' in line:
                solution_found = True
                plan_started = False
                # Look ahead for the actual plan
                continue
            
            # The actual plan starts after an empty line following "Solution found!"
            if solution_found and not plan_started and line.strip() == '':
                plan_started = True
                continue
                
            # Collect plan steps (they start with parentheses)
            if plan_started and line.strip().startswith('(') and line.strip().endswith(')'):
                plan_steps.append(line.strip())
            elif plan_started and 'Plan length:' in line:
                # End of plan
                plan_started = False
            elif 'Plan cost:' in line:
                total_cost = line.strip()
            elif 'Total time:' in line:
                print(f"  {line.strip()}")
        
        if plan_steps:
            print(f"\n📋 Plan ({len(plan_steps)} steps):")
            for i, step in enumerate(plan_steps, 1):
                # Parse the step to make it more readable
                step_clean = step.strip('()')
                parts = step_clean.split()
                if parts[0] == 'move':
                    print(f"  {i}. Move {parts[1]} from {parts[2]} to {parts[3]}")
                elif parts[0] == 'observe':
                    print(f"  {i}. {parts[1]} observes {parts[2]}")
                else:
                    print(f"  {i}. {step}")
            if total_cost:
                print(f"\n  {total_cost}")
        else:
            # Try alternative parsing for sas_plan file
            if os.path.exists('sas_plan'):
                print("\n📋 Reading plan from sas_plan file:")
                with open('sas_plan', 'r') as f:
                    plan_content = f.read().strip()
                    plan_lines = [line for line in plan_content.split('\n') if line.strip().startswith('(')]
                    if plan_lines:
                        plan_steps = plan_lines
                        for i, step in enumerate(plan_steps, 1):
                            step_clean = step.strip('()')
                            parts = step_clean.split()
                            if parts[0] == 'move':
                                print(f"  {i}. Move {parts[1]} from {parts[2]} to {parts[3]}")
                            elif parts[0] == 'observe':
                                print(f"  {i}. {parts[1]} observes {parts[2]}")
                            else:
                                print(f"  {i}. {step}")
        
        # Save plan to file
        if plan_steps:
            with open('solution_plan.txt', 'w') as f:
                f.write(f"Problem: {problem_file}\n")
                f.write(f"Search: {search_algorithm}\n\n")
                f.write("=== PLAN ===\n")
                for i, step in enumerate(plan_steps, 1):
                    step_clean = step.strip('()')
                    parts = step_clean.split()
                    if parts[0] == 'move':
                        f.write(f"{i}. Move {parts[1]} from {parts[2]} to {parts[3]}\n")
                    elif parts[0] == 'observe':
                        f.write(f"{i}. {parts[1]} observes {parts[2]}\n")
                    else:
                        f.write(f"{i}. {step}\n")
                if total_cost:
                    f.write(f"\n{total_cost}\n")
            print("\n💾 Plan saved to solution_plan.txt")
        
    else:
        print("\n❌ No solution found or error occurred")
        print("Error output:", result.stderr)
        if "out of memory" in result.stderr.lower():
            print("\n💡 Try a simpler search algorithm like --search 'eager_greedy([ff()])'")

def generate_domain():
    """Generate the exploration domain"""
    return """(define (domain exploration)
    (:requirements :strips :typing :equality :action-costs)
    
    (:types
        robot location - object
    )
    
    (:predicates
        (at ?r - robot ?l - location)
        (explored ?l - location)
        (adjacent ?l1 - location ?l2 - location)
        (can-traverse ?r - robot ?l - location)
        (can-observe ?r - robot ?l - location)
    )
    
    (:functions
        (total-cost)
        (traverse-cost ?r - robot ?l - location)
    )
    
    (:action move
        :parameters (?r - robot ?from - location ?to - location)
        :precondition (and
            (at ?r ?from)
            (adjacent ?from ?to)
            (can-traverse ?r ?to)
        )
        :effect (and
            (not (at ?r ?from))
            (at ?r ?to)
            (increase (total-cost) (traverse-cost ?r ?to))
        )
    )
    
    (:action observe
        :parameters (?r - robot ?l - location)
        :precondition (and
            (at ?r ?l)
            (can-observe ?r ?l)
        )
        :effect (explored ?l)
    )
)"""

def generate_problem_from_config(config):
    """Generate problem from config"""
    lines = ["(define (problem exploration-generated)",
             "    (:domain exploration)",
             "    ",
             "    (:objects"]
    
    # Add robots
    robot_names = " ".join(config['robots'].keys())
    lines.append(f"        {robot_names} - robot")
    
    # Add locations
    grid_size = config['grid_size']
    locations = []
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            locations.append(f"l{row}{col}")
    
    for i in range(0, len(locations), 9):
        chunk = " ".join(locations[i:i+9])
        if i + 9 >= len(locations):
            chunk += " - location"
        lines.append(f"        {chunk}")
    
    lines.extend(["    )",
                  "    ",
                  "    (:init"])
    
    # Robot starting positions
    lines.append("        ;; Robot starting positions")
    for robot, props in config['robots'].items():
        start_row, start_col = props['start']
        lines.append(f"        (at {robot} l{start_row}{start_col})")
    
    # Get terrain info
    default_terrain = config['terrain_map'].get('default', 'normal')
    special_terrains = config['terrain_map'].get('special', {})
    terrain_costs = config['terrain_types']
    
    # Build traversability and costs
    lines.append("\n        ;; Traversability and costs")
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            loc = f"l{row}{col}"
            
            # Determine terrain type
            terrain = default_terrain
            for key, value in special_terrains.items():
                if (isinstance(key, str) and key == f"[{row}, {col}]") or \
                   (isinstance(key, (list, tuple)) and key == [row, col]):
                    terrain = value
                    break
            
            # Set traversability and costs
            for robot, props in config['robots'].items():
                if terrain in props['can_traverse']:
                    lines.append(f"        (can-traverse {robot} {loc})")
                    cost = terrain_costs[terrain]['cost']
                    lines.append(f"        (= (traverse-cost {robot} {loc}) {cost})")
    
    # Build observation capabilities
    lines.append("\n        ;; Observation capabilities")
    
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            loc = f"l{row}{col}"
            
            # Determine terrain type
            terrain = default_terrain
            for key, value in special_terrains.items():
                if (isinstance(key, str) and key == f"[{row}, {col}]") or \
                   (isinstance(key, (list, tuple)) and key == [row, col]):
                    terrain = value
                    break
            
            # Set observation based on terrain type and robot capabilities
            for robot, props in config['robots'].items():
                if terrain in props['can_observe']:
                    lines.append(f"        (can-observe {robot} {loc})")
    
    # Grid adjacency
    lines.append("\n        ;; Grid adjacency")
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            if col < grid_size:
                lines.append(f"        (adjacent l{row}{col} l{row}{col+1}) "
                           f"(adjacent l{row}{col+1} l{row}{col})")
            if row < grid_size:
                lines.append(f"        (adjacent l{row}{col} l{row+1}{col}) "
                           f"(adjacent l{row+1}{col} l{row}{col})")
    
    lines.append("\n        (= (total-cost) 0)")
    lines.append("    )")
    
    # Goal
    lines.extend(["    ",
                  "    (:goal (and"])
    
    if config['goal'].get('all_explored', False):
        lines.append("        ;; All locations explored")
        for row in range(1, grid_size + 1):
            line = "        "
            for col in range(1, grid_size + 1):
                line += f"(explored l{row}{col}) "
            lines.append(line.rstrip())
    
    if 'robot_positions' in config['goal']:
        lines.append("        ;; Robot goal positions")
        for robot, pos in config['goal']['robot_positions'].items():
            row, col = pos
            lines.append(f"        (at {robot} l{row}{col})")
    
    lines.extend(["    ))",
                  "    ",
                  "    (:metric minimize (total-cost))",
                  ")"])
    
    return "\n".join(lines)

def create_default_config():
    """Create default configuration file"""
    config = """# Exploration problem configuration
grid_size: 3

robots:
  B:
    start: [1, 1]
    can_traverse: [normal, restricted, rocky]
    can_observe: [normal, rocky, restricted]
  G:
    start: [1, 1]
    can_traverse: [normal, rocky]
    can_observe: [normal, rocky, restricted]

terrain_types:
  normal:
    cost: 1
  rocky:
    cost: 5
  restricted:
    cost: 1

terrain_map:
  default: normal
  special:
    "[1, 2]": restricted  # only B can traverse
    "[2, 2]": rocky      # expensive (cost 5)

goal:
  all_explored: true
  robot_positions:
    B: [3, 3]
    G: [3, 3]
"""
    with open('terrain_config.yaml', 'w') as f:
        f.write(config)
    print("✓ Created terrain_config.yaml")


def main():
    """Main workflow"""
    print("🤖 Exploration Problem Solver")
    print("=" * 40)
    
    # Check Docker
    if not check_docker():
        print("❌ Docker not found. Please install Docker first.")
        sys.exit(1)
    
    # Check if config exists
    if not os.path.exists('terrain_config.yaml'):
        print("📝 No terrain_config.yaml found. Creating default...")
        create_default_config()
    
    # Load config
    with open('terrain_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"\n📊 Configuration:")
    print(f"  • Grid: {config['grid_size']}x{config['grid_size']}")
    print(f"  • Robots: {', '.join(config['robots'].keys())}")
    print(f"  • Terrain types: {', '.join(config['terrain_types'].keys())}")
    
    # Generate PDDL files
    print("\n📄 Generating PDDL files...")
    domain = generate_domain()
    problem = generate_problem_from_config(config)
    
    with open('explorationDomain.pddl', 'w') as f:
        f.write(domain)
    print("  ✓ explorationDomain.pddl")
    
    with open('explorationProblem.pddl', 'w') as f:
        f.write(problem)
    print("  ✓ explorationProblem.pddl")
    
    # Setup Docker and solve
    print("\n🐳 Setting up Docker environment...")
    try:
        setup_docker_container()
        
        # Try different search algorithms
        algorithms = [
            ("astar(add())", "A* with additive heuristic"),
            ("eager_greedy([ff()])", "Greedy best-first with FF heuristic"),
            ("astar(lmcut())", "A* with landmark cut heuristic")
        ]
        
        solved = False
        for algo, desc in algorithms:
            if not solved:
                print(f"\n🔍 Trying {desc}...")
                try:
                    solve_with_docker('explorationDomain.pddl', 'explorationProblem.pddl', algo)
                    solved = True
                    break
                except Exception as e:
                    print(f"  Failed with {algo}: {e}")
        
        if not solved:
            print("\n❌ Could not find a solution with any algorithm")

            
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 You can also solve manually:")
        print("  1. Start container: ./docker/run.sh")
        print("  2. Inside container: /opt/downward/fast-downward.py explorationDomain.pddl explorationProblem.pddl --search 'astar(add())'")

if __name__ == "__main__":
    # Install dependencies if needed
    try:
        import yaml
    except ImportError:
        print("Installing PyYAML...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyyaml'])
        import yaml
    
    main()