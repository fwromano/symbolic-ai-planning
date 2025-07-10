#!/bin/bash
# Check what options Fast Downward actually supports

echo "Checking Fast Downward help..."
docker run --rm fast-downward /opt/downward/fast-downward.py --help | grep -E "(time|memory|limit)" | head -20

echo -e "\n\nTrying a simple run without any limit options:"
docker run --rm \
  -v $(pwd):/data:ro \
  fast-downward \
  /opt/downward/fast-downward.py \
  /data/explorationDomain.pddl \
  /data/problems/exploration/exp-2x2.pddl \
  --search "eager_greedy([ff()])"