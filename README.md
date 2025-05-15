## PDDL Examples

### Instructions  
1. Build Docker image:  
`cd docker`  
`docker compose -f compose.yaml build`  

2. Create Docker container: `./run.sh`  

3. Run Fast Downward solver with PDDL domain and problem files:  
`/opt/downward/fast-downward.py <PDDL domain file> <PDDL problem file> --search "astar(add())"`  

E0 files: `roadDomain.pddl` and `roadProblem.pddl`  

E1 files: `explorationDomain.pddl` and `explorationProblem.pddl`  

## OWL-Based Planning  

## Instructions  
1. Create Python virtual environment: `virtualenv venv`  

2. Activate virtual environment: `source venv/bin/activate`  

3. Install dependencies: `pip3 install -r requirements.txt`  

4. Run planner: `./roadPlanner.py`

note: exploration sampling run with seed 42 