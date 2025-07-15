#!/usr/bin/env python3
"""
All-in-one script: Config → PDDL → Solution
Aligned with OWL ontology structure
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

def solve_with_docker(domain_file, problem_file, search_config):
    """Solve using Docker container with specified search configuration"""
    search_string = search_config.get('search', 'lazy_wastar([lmcut()], w=3)')
    print(f"\nSolving with search: {search_string}")
    
    # Ensure container is running
    if not container_running('fast-downward'):
        setup_docker_container()
    
    # Copy files to container if needed
    subprocess.run(['docker', 'cp', domain_file, f'fast-downward:/workspace/{domain_file}'])
    subprocess.run(['docker', 'cp', problem_file, f'fast-downward:/workspace/{problem_file}'])
    
    # Build command
    cmd = [
        'docker', 'exec', 'fast-downward',
        '/opt/downward/fast-downward.py',
        f'/workspace/{domain_file}',
        f'/workspace/{problem_file}',
        '--search', search_string
    ]
    
    # Add evaluator if specified
    if 'evaluator' in search_config:
        cmd.extend(['--evaluator', search_config['evaluator']])
    
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
                    # Convert location format for display
                    from_loc = parts[2].replace('l', 'r')  # l11 -> r11 to match OWL
                    to_loc = parts[3].replace('l', 'r')
                    print(f"  {i}. Move {parts[1]} from {from_loc} to {to_loc}")
                elif parts[0] == 'observe':
                    loc = parts[2].replace('l', 'r')
                    print(f"  {i}. {parts[1]} observes {loc}")
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
                                from_loc = parts[2].replace('l', 'r')
                                to_loc = parts[3].replace('l', 'r')
                                print(f"  {i}. Move {parts[1]} from {from_loc} to {to_loc}")
                            elif parts[0] == 'observe':
                                loc = parts[2].replace('l', 'r')
                                print(f"  {i}. {parts[1]} observes {loc}")
                            else:
                                print(f"  {i}. {step}")
        
        # Save plan to file
        if plan_steps:
            with open('solution_plan.txt', 'w') as f:
                f.write(f"Problem: {problem_file}\n")
                f.write(f"Search: {search_string}\n\n")
                f.write("=== PLAN ===\n")
                for i, step in enumerate(plan_steps, 1):
                    step_clean = step.strip('()')
                    parts = step_clean.split()
                    if parts[0] == 'move':
                        from_loc = parts[2].replace('l', 'r')
                        to_loc = parts[3].replace('l', 'r')
                        f.write(f"{i}. Move {parts[1]} from {from_loc} to {to_loc}\n")
                    elif parts[0] == 'observe':
                        loc = parts[2].replace('l', 'r')
                        f.write(f"{i}. {parts[1]} observes {loc}\n")
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
    """Generate the exploration domain (OWL-aligned)"""
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
    """Generate problem from config (OWL-aligned)"""
    lines = ["(define (problem exploration-generated)",
             "    (:domain exploration)",
             "    ",
             "    (:objects"]
    
    # Add robots
    robot_names = " ".join(config['robots'].keys())
    lines.append(f"        {robot_names} - robot")
    
    # Add locations (using l prefix for PDDL, but representing r locations from OWL)
    grid_size = config['grid_size']
    locations = []
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            locations.append(f"l{row}{col}")  # PDDL format, represents r{row}{col} in OWL
    
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
    default_terrain = config['terrain_map'].get('default', 'grass')
    special_terrains = config['terrain_map'].get('special', {})
    terrain_costs = config['terrain_types']
    
    # Build traversability and costs
    lines.append("\n        ;; Traversability and costs (based on terrain types)")
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
            
            # Set traversability and costs based on terrain type
            for robot, props in config['robots'].items():
                if terrain in props.get('can_traverse', []):
                    lines.append(f"        (can-traverse {robot} {loc})")
                    cost = terrain_costs[terrain]['cost']
                    lines.append(f"        (= (traverse-cost {robot} {loc}) {cost})")
    
    # Build observation capabilities
    lines.append("\n        ;; Observation capabilities (based on observation types)")
    
    # Get observation map
    default_obs = config['observation_map'].get('default', 'any')
    special_obs = config['observation_map'].get('special', {})
    
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            loc = f"l{row}{col}"
            
            # Determine observation type for this location
            obs_type = default_obs
            for key, value in special_obs.items():
                if (isinstance(key, str) and key == f"[{row}, {col}]") or \
                   (isinstance(key, (list, tuple)) and key == [row, col]):
                    obs_type = value
                    break
            
            # Set observation capabilities based on observation type
            for robot, props in config['robots'].items():
                if obs_type in props.get('can_observe', []):
                    lines.append(f"        (can-observe {robot} {loc})")
    
    # Grid adjacency (matching OWL's northOf, southOf, eastOf, westOf)
    lines.append("\n        ;; Grid adjacency")
    for row in range(1, grid_size + 1):
        for col in range(1, grid_size + 1):
            # East-West adjacency
            if col < grid_size:
                lines.append(f"        (adjacent l{row}{col} l{row}{col+1}) "
                           f"(adjacent l{row}{col+1} l{row}{col})")
            # North-South adjacency (row 1 is bottom, higher rows are north)
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
    """Create default configuration file aligned with OWL ontology"""
    config = """# Exploration problem configuration (OWL-aligned)
# This configuration matches the E1.min.owl ontology structure

grid_size: 3

robots:
  vehB:  # Blue vehicle (alpha_r in OWL)
    start: [1, 1]  # r11 in OWL
    can_traverse: [grass, gravel, rock]  # agCanTraverseType
    can_observe: [blue, any]  # agCanObserveType
  vehG:  # Green vehicle (alpha_r in OWL)
    start: [1, 1]  # r11 in OWL
    can_traverse: [grass, gravel]  # Cannot traverse rock
    can_observe: [green, any]  # agCanObserveType

terrain_types:  # terrainType in OWL
  grass:
    cost: 1
  gravel:
    cost: 5  # Higher cost terrain
  rock:
    cost: 1  # Note: only vehB can traverse this

observation_map:  # locHasObserveType in OWL
  default: any  # Most locations observable by any robot
  special:
    "[1, 3]": blue   # r13 - only vehB can observe
    "[3, 2]": green  # r32 - only vehG can observe

terrain_map:  # locHasTerrainType in OWL
  default: grass  # Most locations are grass
  special:
    "[1, 2]": rock    # r12 - only vehB can traverse
    "[2, 2]": gravel  # r22 - expensive for both robots

goal:
  all_explored: true  # All locations must be observed
  robot_positions:
    vehB: [3, 3]  # r33 in OWL
    vehG: [3, 3]  # r33 in OWL
"""
    with open('terrain_config.yaml', 'w') as f:
        f.write(config)
    print("✓ Created terrain_config.yaml (OWL-aligned)")

def get_search_configs():
    """Get available search configurations"""
    return {
        'optimal': [
            {
                'name': 'A* with LM-cut',
                'search': 'astar(lmcut())',
                'description': 'Optimal planner with landmark cut heuristic'
            },
            {
                'name': 'A* with merge-and-shrink',
                'search': 'astar(merge_and_shrink())',
                'description': 'Optimal planner with merge-and-shrink abstraction'
            },
            {
                'name': 'A* with iPDB',
                'search': 'astar(ipdb())',
                'description': 'Optimal planner with pattern database heuristic'
            }
        ],
        'satisficing': [
            {
                'name': 'Greedy FF',
                'search': 'eager_greedy([ff()])',
                'description': 'Fast satisficing search with FF heuristic'
            },
            {
                'name': 'Greedy add',
                'search': 'eager_greedy([add()])',
                'description': 'Fast satisficing search with additive heuristic'
            },
            {
                'name': 'Lazy greedy FF',
                'search': 'lazy_greedy([ff()])',
                'description': 'Lazy satisficing search with FF heuristic'
            },
            {
                'name': 'LAMA-first',
                'search': 'lazy_greedy([lama_ff_syn()], preferred=[lama_ff_syn()])',
                'description': 'LAMA planner - finds solution quickly'
            }
        ],
        'anytime': [
            {
                'name': 'Weighted A* (W=3) with LM-cut',
                'search': 'lazy_wastar([lmcut()], w=3)',
                'description': 'Anytime weighted A* with LM-cut heuristic'
            },
            {
                'name': 'Weighted A* (W=5) with LM-cut',
                'search': 'lazy_wastar([lmcut()], w=5)',
                'description': 'Anytime weighted A* with LM-cut heuristic'
            },
            {
                'name': 'Weighted A* (W=3) with FF',
                'search': 'lazy_wastar([ff()], w=3)',
                'description': 'Anytime weighted A* with FF heuristic'
            }
        ]
    }

def select_search_config():
    """Interactive selection of search configuration"""
    configs = get_search_configs()
    
    print("\n🔍 Select search strategy:")
    print("1. Optimal (guarantees shortest plan)")
    print("2. Satisficing (finds solution quickly)")
    print("3. Anytime (improves solution over time)")
    print("4. Custom (enter your own)")
    
    choice = input("\nChoice (1-4) [default=3]: ").strip() or "3"
    
    if choice == "4":
        search = input("Enter search string (e.g., 'astar(lmcut())'): ").strip()
        return {'name': 'Custom', 'search': search}
    
    category_map = {'1': 'optimal', '2': 'satisficing', '3': 'anytime'}
    if choice not in category_map:
        print("Invalid choice, using default anytime search")
        choice = '3'
    
    category = category_map[choice]
    options = configs[category]
    
    print(f"\nAvailable {category} planners:")
    for i, config in enumerate(options, 1):
        print(f"{i}. {config['name']}: {config['description']}")
    
    planner_choice = input(f"\nChoice (1-{len(options)}) [default=1]: ").strip() or "1"
    
    try:
        idx = int(planner_choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass
    
    print("Invalid choice, using first option")
    return options[0]

def main():
    """Main workflow"""
    print("🤖 OWL-Aligned Exploration Problem Solver")
    print("=" * 40)
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Solve exploration planning problems (OWL-aligned)')
    parser.add_argument('--config', default='terrain_config.yaml', help='Configuration file')
    parser.add_argument('--auto', action='store_true', help='Run without prompts')
    parser.add_argument('--search', help='Search algorithm (e.g., "astar(lmcut())")')
    parser.add_argument('--optimal', action='store_true', help='Use optimal search')
    parser.add_argument('--fast', action='store_true', help='Use fast satisficing search')
    args = parser.parse_args()
    
    # Check Docker
    if not check_docker():
        print("❌ Docker not found. Please install Docker first.")
        sys.exit(1)
    
    # Check if config exists
    if not os.path.exists(args.config):
        print(f"📝 No {args.config} found. Creating default OWL-aligned configuration...")
        create_default_config()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"\n📊 Configuration (OWL-aligned):")
    print(f"  • Grid: {config['grid_size']}x{config['grid_size']}")
    print(f"  • Robots: {', '.join(config['robots'].keys())}")
    print(f"  • Terrain types: {', '.join(config['terrain_types'].keys())}")
    if 'observation_map' in config:
        obs_types = set(['any', 'blue', 'green'])  # Standard observation types
        print(f"  • Observation types: {', '.join(sorted(obs_types))}")
    
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
    
    # Select search configuration
    if args.search:
        search_config = {'name': 'Custom', 'search': args.search}
    elif args.optimal:
        search_config = {'name': 'A* with LM-cut', 'search': 'astar(lmcut())'}
    elif args.fast:
        search_config = {'name': 'Greedy FF', 'search': 'eager_greedy([ff()])'}
    else:
        # Default to weighted A* with LM-cut - no prompts
        search_config = {'name': 'Weighted A* (W=3) with LM-cut', 'search': 'lazy_wastar([lmcut()], w=3)'}
    
    print(f"\n🔧 Using: {search_config['name']}")
    
    # Setup Docker and solve
    print("\n🐳 Setting up Docker environment...")
    try:
        setup_docker_container()
        solve_with_docker('explorationDomain.pddl', 'explorationProblem.pddl', search_config)
            
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