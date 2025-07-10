# Profiling Methodology for Symbolic AI Planning

This document details the comprehensive profiling methodology used to analyze the empirical complexity of planning problems in the symbolic AI planning project.

## Overview

The profiling system consists of a complete pipeline:
1. **Problem Generation** - Creates PDDL problem instances of varying sizes
2. **Execution & Measurement** - Runs Fast Downward planner in Docker containers
3. **Data Collection** - Captures metrics like runtime, nodes expanded, and plan length
4. **Analysis & Visualization** - Generates graphs and complexity analysis reports

## 1. Road Domain Profiling

### 1.1 Problem Generation
The road domain problems are generated using `analysis/road_problem_gen.py`:

```bash
# Generate a single problem
python road_problem_gen.py --segments 100 --out road-100.pddl

# Generate batch with log2 distribution
python road_problem_gen.py --segments-max 16384 --batch-log2 --out-dir problems/
```

**Problem Structure:**
- Linear road with n segments (locations l1 to l(n+1))
- Two vehicles: v1 (regular) and v2 (bulldozer)
- Rubble blocking location l2
- Goal: Push v1 to final location l(n+1)

### 1.2 Profiling Execution
The profiling is performed by `docker/road_complexity_analysis.py`:

```bash
python docker/road_complexity_analysis.py roadDomain.pddl problems \
       --docker-image fast-downward \
       --mount "$(pwd)"
```

**Key Features:**
- Uses Fast Downward with A* search and additive heuristic: `astar(add())`
- Supports two Docker modes:
  - `docker run`: Fresh container per problem (stateless)
  - `docker exec`: Reuse existing container (faster for many problems)
- Measures wall-clock runtime for each problem instance

### 1.3 Metrics Collected
For each problem instance:
- **Segments**: Number of road segments (problem size)
- **Plan Length**: Number of actions in the solution
- **Nodes Expanded**: States explored during search
- **Runtime**: Total execution time in seconds

### 1.4 Data Processing
The script automatically:
1. Parses Fast Downward output using regex patterns
2. Saves results to CSV file (`road_metrics.csv`)
3. Generates initial runtime plot (`runtime_vs_size.png`)

## 2. Exploration Domain Profiling

### 2.1 Problem Generation
Exploration problems are generated using `analysis/exploration_problem_gen.py`:

```bash
# Generate single NxN grid
python exploration_problem_gen.py --grid 4 --out exp-4x4.pddl

# Generate batch with various sizes
python exploration_problem_gen.py --batch --batch-max 32 --out-dir problems/
```

**Problem Structure:**
- NxN grid of locations
- Multiple robots with different capabilities
- ~10% high-cost terrain
- ~10% locations require specific robot for traversal
- ~10% locations require specific robot for observation
- Goal: Visit and observe all locations

### 2.2 Profiling Execution
The profiling uses `docker/exploration_complexity_analysis.py`:

```bash
python docker/exploration_complexity_analysis.py explorationDomain.pddl problems \
       --docker-image fast-downward \
       --mount "$(pwd)"
```

**Key Differences from Road Domain:**
- Uses landmark-cut heuristic: `astar(lmcut())`
- Handles both `exp-NxN.pddl` and `explore-NxN.pddl` naming patterns
- Extracts grid size from filename

### 2.3 Metrics and Processing
Same metrics as road domain:
- Grid size (N for NxN grid)
- Plan length, nodes expanded, runtime
- Output: `explore_metrics.csv` and `explore_runtime_vs_size.png`

## 3. Analysis Pipeline

### 3.1 Visualization Generation
The `analysis/analysis_graphs.py` script creates detailed visualizations:

1. **Plan Length & Nodes Graph** (`graph_plan_vs_nodes.png`)
   - Log-scale X-axis for problem size
   - Shows linear growth patterns

2. **Runtime Linear Scale** (`graph_runtime_linear.png`)
   - Linear X and Y axes
   - Reveals acceleration in runtime growth

3. **Runtime Log Scale** (`graph_runtime_logx.png`)
   - Log X-axis, linear Y-axis
   - Better visibility across size ranges

4. **Power Law Fit** (`graph_power_law_fit.png`)
   - Log-log plot with linear regression
   - Determines growth exponent (e.g., n^1.4)

### 3.2 Report Generation
Analysis results are documented in markdown reports:
- `road_analysis.md` - Complete road domain analysis
- `exploration_analysis.md` - Exploration domain analysis

## 4. Docker Integration

### 4.1 Container Setup
Both profiling scripts use Docker for consistent execution environment:
- **Image**: Fast Downward planner container
- **Mount**: Host directory mounted at `/data` (read-only)
- **Path**: Planner at `/opt/downward/fast-downward.py`

### 4.2 Execution Modes

**Docker Run Mode:**
```python
docker run --rm -v {host_dir}:/data:ro {image} \
    /opt/downward/fast-downward.py \
    /data/{domain} /data/{problem} \
    --search {search_algorithm}
```

**Docker Exec Mode:**
```python
docker exec {container} \
    /opt/downward/fast-downward.py \
    {domain} {problem} \
    --search {search_algorithm}
```

## 5. Performance Considerations

### 5.1 Timing Methodology
- Uses Python's `time.time()` for wall-clock measurement
- Includes entire Docker execution overhead
- Captures both stdout and stderr for parsing

### 5.2 Error Handling
- Validates Docker command success
- Prints debug output on failures
- Skips files that don't match expected patterns

### 5.3 Scalability
- Tested up to 16,384 segments (road domain)
- Memory usage remains manageable (<150MB for largest problems)
- Runtime grows super-linearly (≈n^1.4) for large instances

## 6. Reproducibility

Each analysis can be fully reproduced:

1. **Generate problems**: Use problem generation scripts with same parameters
2. **Run profiling**: Execute complexity analysis script
3. **Create graphs**: Run analysis_graphs.py on resulting CSV
4. **Compare results**: Theoretical predictions vs empirical measurements

The combination of automated problem generation, containerized execution, and systematic data collection ensures consistent and reproducible profiling results across different environments.