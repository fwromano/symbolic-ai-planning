# Fast Downward Search Algorithms Comparison Guide

## Quick Comparison Table

| Algorithm | Speed | Memory | Solution Quality | Completeness | Optimal | Best For | Avoid When |
|-----------|-------|---------|-----------------|--------------|---------|----------|------------|
| **A* (LM-cut)** | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ✅ | Small problems requiring optimal solutions | Large state spaces, time constraints |
| **Greedy Best-First (FF)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | Large problems, satisficing planning | Need quality guarantees |
| **Lazy Greedy (FF)** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ❌ | ❌ | Very large problems, speed critical | Memory constrained systems |
| **Greedy (Add)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ❌ | ❌ | Simple problems, minimal overhead | Complex domains |
| **Lazy W-A* (W=2)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ❌ | Memory-limited systems with quality needs | Strict optimality required |
| **EHC** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ | ❌ | Very large problems, linear planning | Domains with many dead ends |
| **Lazy W-A* (W=3)** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ | ❌ | General purpose satisficing | Need <3x optimal guarantee |
| **Lazy W-A* (W=5)** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ | ❌ | Speed important, quality secondary | Quality critical applications |
| **Eager W-A* (W=3)** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ | ❌ | Predictable memory usage needed | Very large state spaces |
| **Greedy (CG)** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ❌ | ❌ | Structured domains, causal chains | Highly interconnected problems |
| **Iterated W-A*** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ❌ | Anytime planning, iterative improvement | Hard time constraints |
| **Restart W-A*** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ❌ | Anytime planning with restarts | Single-shot planning |

### Legend:
- **Speed/Memory**: ⭐ (worst) to ⭐⭐⭐⭐⭐ (best)
- **Solution Quality**: ⭐ (poor) to ⭐⭐⭐⭐⭐ (optimal)
- **Completeness**: ✅ = Guaranteed to find solution if exists, ❌ = May fail on solvable problems
- **Optimal**: ✅ = Finds shortest/cheapest plan, ❌ = May find suboptimal plans

---

## Detailed Algorithm Descriptions

### 1. A* with LM-cut Heuristic (Optimal)
**Search**: `astar(lmcut())`

**Overview**: The gold standard for optimal planning. Uses the landmark cut heuristic, one of the most informative admissible heuristics available.

**Characteristics**:
- **Pros**: 
  - Guarantees optimal solutions
  - Complete (will find a solution if one exists)
  - LM-cut is highly informative, reducing search effort
- **Cons**: 
  - Very slow on large problems
  - High memory usage for storing open/closed lists
  - Computing LM-cut is expensive

**When to use**:
- Small to medium problems (typically <10,000 states)
- Optimality is critical (e.g., minimizing fuel consumption, cost)
- Benchmark comparisons

**When to avoid**:
- Large state spaces (>100,000 states)
- Real-time planning scenarios
- When any valid solution suffices

---

### 2. Greedy Best-First Search (FF Heuristic)
**Search**: `eager_greedy([ff()])`

**Overview**: Uses the Fast-Forward (FF) heuristic in a greedy best-first search. Eager evaluation means nodes are fully evaluated when generated.

**Characteristics**:
- **Pros**: 
  - Very fast on most domains
  - FF heuristic is informative and quick to compute
  - Good solution quality in practice
  - Predictable memory usage
- **Cons**: 
  - Not complete (can get stuck in dead ends)
  - No optimality guarantees
  - Can use significant memory on hard problems

**When to use**:
- Large planning problems
- Domains where FF heuristic works well (most STRIPS-like domains)
- Need fast solutions with reasonable quality

**When to avoid**:
- Domains with many dead ends
- Need completeness guarantees
- Optimality required

---

### 3. Lazy Greedy Best-First (FF Heuristic)
**Search**: `lazy_greedy([ff()], preferred=[ff()])`

**Overview**: Defers heuristic evaluation until node expansion. Uses preferred operators from FF heuristic to guide search.

**Characteristics**:
- **Pros**: 
  - Often fastest algorithm for satisficing planning
  - Preferred operators significantly boost performance
  - Can handle very large problems
- **Cons**: 
  - Higher memory usage due to lazy evaluation
  - Not complete
  - Less predictable than eager version

**When to use**:
- Very large problems where speed is critical
- Domains with clear preferred operator structure
- Initial solution finding in anytime planning

**When to avoid**:
- Memory-constrained environments
- Need predictable resource usage
- Domains where FF heuristic misleads

---

### 4. Greedy Best-First (Additive Heuristic)
**Search**: `eager_greedy([add()])`

**Overview**: Uses the simple additive heuristic (h^add), which sums costs ignoring negative interactions.

**Characteristics**:
- **Pros**: 
  - Very fast heuristic computation
  - Low memory overhead
  - Works well on simple domains
- **Cons**: 
  - Less informative than FF
  - Often finds lower quality solutions
  - Can expand many more nodes

**When to use**:
- Very simple planning problems
- When heuristic computation time dominates
- Minimal resource usage needed

**When to avoid**:
- Complex domains with interactions
- When solution quality matters
- Problems requiring good guidance

---

### 5. Lazy Weighted A* (W=2)
**Search**: `lazy_wastar([ff()], w=2)`

**Overview**: A* variant that inflates heuristic by factor of 2. Trades optimality for speed while maintaining completeness.

**Characteristics**:
- **Pros**: 
  - Complete algorithm
  - Solutions at most 2x optimal cost
  - Low memory due to lazy evaluation
  - Good speed/quality trade-off
- **Cons**: 
  - Slower than pure greedy approaches
  - Still may timeout on very large problems

**When to use**:
- Need completeness with bounded suboptimality
- Memory-constrained systems
- Good general-purpose choice

**When to avoid**:
- Need optimal solutions
- Speed is absolutely critical
- Can tolerate incomplete algorithms

---

### 6. Enforced Hill-Climbing (EHC)
**Search**: `ehc([ff()])`

**Overview**: Performs breadth-first search to find improving states, then commits to them. Extremely memory efficient.

**Characteristics**:
- **Pros**: 
  - Minimal memory usage
  - Very fast on suitable domains
  - Good for domains with clear improvement paths
- **Cons**: 
  - Highly incomplete
  - Can fail on solvable problems
  - No quality guarantees

**When to use**:
- Extremely large problems
- Domains with monotonic improvement structure
- Memory is severely limited

**When to avoid**:
- Domains with local minima
- Need any completeness guarantee
- Problems requiring backtracking

---

### 7. Lazy Weighted A* (W=3)
**Search**: `lazy_wastar([ff()], w=3)`

**Overview**: Balanced weighted A* with 3x optimality bound. Good general-purpose satisficing planner.

**Characteristics**:
- **Pros**: 
  - Complete with bounded suboptimality
  - Good balance of speed and quality
  - Handles most domains well
- **Cons**: 
  - 3x bound may be too loose for some applications
  - Still slower than greedy on easy problems

**When to use**:
- General satisficing planning
- Unknown domain characteristics
- Need completeness but not optimality

**When to avoid**:
- Very easy problems (use greedy)
- Very hard problems (may timeout)
- Need tighter quality bounds

---

### 8. Lazy Weighted A* (W=5)
**Search**: `lazy_wastar([ff()], w=5)`

**Overview**: Aggressive weighted A* prioritizing speed over quality. 5x optimality bound.

**Characteristics**:
- **Pros**: 
  - Fast while maintaining completeness
  - Good for finding any solution quickly
  - Still provides bounded suboptimality
- **Cons**: 
  - Solutions can be quite suboptimal
  - May still be too slow for huge problems

**When to use**:
- Need fast complete algorithm
- Solution quality less important
- First phase of anytime planning

**When to avoid**:
- Quality matters significantly
- Greedy algorithms work well
- Very tight time constraints

---

### 9. Eager Weighted A* (W=3)
**Search**: `eager_wastar([ff()], w=3)`

**Overview**: Eager evaluation version of weighted A*. More predictable memory usage than lazy version.

**Characteristics**:
- **Pros**: 
  - Predictable memory consumption
  - Complete with bounds
  - No deferred computation overhead
- **Cons**: 
  - Generally slower than lazy version
  - May evaluate more nodes
  - Higher heuristic computation cost

**When to use**:
- Need predictable resource usage
- Embedded systems planning
- Debugging/analysis purposes

**When to avoid**:
- Very large state spaces
- Speed is critical
- Memory not a concern

---

### 10. Greedy Best-First (Causal Graph Heuristic)
**Search**: `eager_greedy([cg()])`

**Overview**: Uses domain structure via causal graph analysis. Good for domains with clear causal chains.

**Characteristics**:
- **Pros**: 
  - Exploits domain structure
  - Fast on hierarchical domains
  - Different perspective than FF/add
- **Cons**: 
  - Less general than FF
  - Can miss interactions
  - Not complete

**When to use**:
- Domains with clear causal structure
- Hierarchical planning problems
- When FF fails

**When to avoid**:
- Highly interconnected domains
- No clear causal chains
- General-purpose planning

---

### 11. Iterated Weighted A*
**Search**: `iterated([lazy_wastar([ff()], w=5), lazy_wastar([ff()], w=3), lazy_wastar([ff()], w=2)])`

**Overview**: Anytime algorithm that runs increasingly less greedy searches. Finds solution quickly then improves it.

**Characteristics**:
- **Pros**: 
  - Anytime behavior
  - Progressive quality improvement
  - Good for unknown time budgets
- **Cons**: 
  - Overhead of multiple searches
  - May waste time on easy problems
  - Complex to tune

**When to use**:
- Unknown time budget
- Can use solutions as found
- Quality matters but not critical

**When to avoid**:
- Fixed short deadline
- Need single best effort
- Very easy or very hard problems

---

### 12. Restarting Weighted A*
**Search**: `lazy_wastar([ff()], w=5, repeat_last=true)`

**Overview**: Restarts search with tighter bounds when solutions found. Automatic anytime behavior.

**Characteristics**:
- **Pros**: 
  - Automatic bound tightening
  - No manual configuration needed
  - Good anytime properties
- **Cons**: 
  - Restart overhead
  - May not improve much
  - Less control than iterated

**When to use**:
- Want anytime without configuration
- Iterative improvement scenarios
- Flexible time budgets

**When to avoid**:
- Need specific bound progression
- Very tight time limits
- Single-shot planning

---

## Domain-Specific Recommendations

### For Grid/Pathfinding Problems (like exploration domain):
1. **First choice**: Lazy Greedy (FF) - Usually extremely fast
2. **If quality matters**: Lazy W-A* (W=3)
3. **If optimal needed**: A* (LM-cut) - Only for small grids

### For Logistics/Transportation:
1. **First choice**: Greedy (FF) or Lazy Greedy (FF)
2. **Backup**: EHC often works well
3. **Quality**: Weighted A* variants

### For Robot Manipulation:
1. **First choice**: Lazy W-A* (W=3) - Good balance
2. **If hierarchical**: Greedy (CG)
3. **Anytime**: Iterated W-A*

### For Unknown Domains:
1. **Start with**: Lazy W-A* (W=3) - Most robust
2. **If too slow**: Lazy Greedy (FF)
3. **If fails**: Try different heuristics (CG, add)

## Memory and Time Complexity

| Algorithm | Time Complexity | Space Complexity | Typical Timeout | Typical Memory |
|-----------|----------------|------------------|-----------------|----------------|
| A* (LM-cut) | O(b^d) | O(b^d) | 30-300s | 100MB-8GB |
| Greedy (FF) | O(b^m) worst | O(b×d) | 10-60s | 50MB-2GB |
| Lazy Greedy | O(b^m) worst | O(b×d) | 10-60s | 100MB-4GB |
| W-A* | O(b^d) | O(b^d) | 30-180s | 100MB-4GB |
| EHC | O(b×d) | O(d) | 10-30s | 10MB-500MB |

Where:
- b = branching factor
- d = optimal solution depth  
- m = maximum depth searched