# Grid Cell Shape Caching Strategy

## Overview

This document describes the caching strategy for grid-cell level hourly capacity factor profiles used in renewable energy profile generation.

**Last Updated:** October 30, 2025  
**Status:** Active Implementation

---

## The Problem

### Challenge
Users interact with a simulator UI that allows dynamic capacity adjustments for renewable energy sources (solar, wind, offshore wind). Each adjustment requires:

1. **Cell Selection:** Select optimal grid cells based on capacity target (merit order by CF)
2. **Profile Generation:** Fetch 8760-hour CF profiles for selected cells
3. **Aggregation:** Calculate hourly generation and aggregate across cells

**Performance Issue:**
- Grid cell shapes stored in large parquet file (`atlite_grid_cell_2013.parquet`)
- Loading shapes from parquet is slow (2-3 seconds per ISO)
- Users adjust capacity frequently → repeated disk I/O is prohibitive
- 100 concurrent users could request 100 different ISOs

---

## The Solution: LRU Cache with Incremental Loading

### Strategy Overview

**Incremental cache building - Load only what's needed:**
1. When cells are requested, check if they're already cached
2. Load ONLY missing cells from parquet (targeted read)
3. Merge new cells with existing cache (cache grows naturally)
4. Subsequent requests for same cells = instant memory lookup
5. Use LRU (Least Recently Used) eviction when memory limit reached

### Why LRU?

**LRU = "Least Recently Used" eviction policy**

Popular ISOs (DEU, USA, CHN) requested frequently → stay cached permanently  
Rare ISOs (small countries) requested infrequently → get evicted when cache full

**Alternative rejected: FIFO (First In First Out)**
- Would evict ISOs based on insertion order, not usage frequency
- Popular ISO added first → evicted despite high demand
- Poor cache hit rate in production

---

## Technical Architecture

### Cache Structure

```python
class GridCellShapeCache:
    """
    LRU cache for grid-cell level hourly CF profiles
    
    Features:
    - Shared across all API users (singleton pattern)
    - Automatic eviction of least-used ISOs
    - Memory-bounded (configurable limit)
    - Per-technology caching (solar, wind, windoff separate)
    """
    
    _cache = OrderedDict()  # {f"{iso}_{tech}": {cell_id: np.array(8760)}}
    _max_isos = 10          # Keep up to 10 ISO+tech combinations
    _max_memory_gb = 3      # ~3 GB memory limit
```

### Memory Estimation

```
Per grid cell: 8760 hours × 8 bytes (float64) = 70 KB

Typical usage patterns:
- 10 GW capacity: ~15 cells = 1 MB
- 20 GW capacity: ~30 cells = 2 MB
- 50 GW capacity: ~100 cells = 7 MB
- 100 GW capacity: ~200 cells = 14 MB

Cache capacity (10 ISO+tech combinations):
- Typical: 10-100 MB (efficient!)
- Maximum if all heavily used: 1-3 GB

Memory savings vs loading all cells: 10-30x improvement!
```

### Loading Strategy

**Incremental loading (smart and efficient):**

```python
# ✅ SMART: Load only missing cells
def get_cell_shapes(iso_code, technology, cell_ids):
    if cache_key in cache:
        # Check which cells are missing
        missing = [c for c in cell_ids if c not in cache[cache_key]]
        
        if missing:
            # Load ONLY missing cells (targeted read)
            new_shapes = load_from_parquet(missing)
            
            # Merge with existing cache
            cache[cache_key].update(new_shapes)
        
        return cache[cache_key]
    
    # First request: load requested cells
    shapes = load_from_parquet(cell_ids)
    cache[cache_key] = shapes
    return shapes
```

**Why this works:**
- Only loads what's actually needed
- Cache grows naturally with usage
- Fast initial loads (0.5s for 15 cells vs 3s for 2000 cells)
- User adjusts capacity up → loads additional cells only
- User adjusts capacity down → cache hit, instant!

---

## Production Behavior

### Multi-User Scenario

**100 concurrent users, mixed ISOs:**

```
Time 0: Cache empty []

User 1 (DEU, 10 GW) → Load 15 cells, cache DEU: {15 cells}
User 2 (USA, 5 GW) → Load 10 cells, cache USA: {10 cells}
User 3 (DEU, 10 GW) → Cache hit! All 15 cells found
User 4 (DEU, 20 GW) → Partial hit! 15 cached, load 15 more → cache DEU: {30 cells}
User 5 (CHN, 10 GW) → Load 15 cells, cache CHN: {15 cells}
...
User 50 (JPN, 30 GW) → Cache full, evict least-used, load 45 cells
User 51 (DEU, 15 GW) → Cache hit! All 22 cells found (DEU still popular)
```

### Cache Hit Rate

**Typical production pattern:**
- 10 most popular ISOs = 80-90% of all requests (Pareto principle)
- Cache size: 10 slots
- **Effective hit rate: 85-95%** (full hits + partial hits)

**User experience breakdown:**
- 60-70% of requests: **Full cache hit** (all cells found, 0.01s)
- 15-25% of requests: **Partial cache hit** (some cells found, load rest, 0.2-1s)
- 10-15% of requests: **Cache miss** (load all requested cells, 0.5-2s)

**Three types of cache outcomes:**
1. **Full hit**: All cells already cached → Instant ⚡
2. **Partial hit**: Some cells cached, load missing → Fast 🚀
3. **Miss**: No cache entry, load requested cells → Acceptable ✅

### Memory Safety

**Bounded memory usage:**
- Max ISOs: 10 (configurable)
- Typical memory: 10-100 MB per ISO (vs 140-700 MB for full loading)
- Total cache: Usually 50-500 MB (vs 1-3 GB)
- Server won't crash even with 1,000 concurrent users
- Automatic eviction prevents memory exhaustion
- **30x more memory efficient than loading all cells!**

---

## Performance Comparison

### Scenario: User adjusts Germany solar capacity

**Sequence: 10 GW → 20 GW → 50 GW → 20 GW → 10 GW**

**No caching:**
```
10 GW: Load 15 cells (0.5s)
20 GW: Load 30 cells (1s)
50 GW: Load 100 cells (3s)
20 GW: Load 30 cells (1s)
10 GW: Load 15 cells (0.5s)
Total: 6 seconds 😱
```

**With incremental LRU cache:**
```
10 GW: Load 15 cells (0.5s) → cache: {15 cells}
20 GW: Load 15 MORE cells (0.5s) → cache: {30 cells} [partial hit]
50 GW: Load 70 MORE cells (2s) → cache: {100 cells} [partial hit]
20 GW: Cache hit! (0.01s) [full hit]
10 GW: Cache hit! (0.01s) [full hit]
Total: 3.02 seconds 🚀

2x speedup + only 7 MB memory!
```

### Memory Comparison

**Full loading approach (old):**
```
Load ALL cells for ISO: 2000 cells = 140 MB
5 ISOs: 700 MB
10 ISOs: 1-3 GB
```

**Incremental loading (current):**
```
Load only what's used:
- 10 GW typical: 15 cells = 1 MB
- 50 GW heavy: 100 cells = 7 MB
5 ISOs @ 10 GW each: 5 MB
50 ISOs @ 10 GW each: 50 MB

10-30x more memory efficient! 🎉
```

---

## Implementation Phases

### Phase 1: Incremental LRU Cache ✅ (Current)

**Implementation:**
- `shared_data_loader.py`: `GridCellShapeCache` with incremental loading
- `8760_supply_demand_constructor.py`: Profile generation with error handling
- `api_server.py`: Hourly profile endpoints

**Key Features:**
- Load only missing cells (targeted parquet reads)
- Merge with existing cache (cache grows naturally)
- Track full hits, partial hits, and misses
- Proper error handling (raises ValueError on missing data)

**Testing:**
- Monitor memory usage (should be 10-30x lower than full loading)
- Track cache hit rates (effective hit rate should be 85-95%)
- Adjust `max_isos` based on actual patterns

### Phase 2: Pre-computed Files (Future Enhancement)

**If needed for performance:**
```bash
# One-time preprocessing
python scripts/precompute_grid_cell_shapes.py

# Converts parquet → .npz format per ISO
# Load time: 100ms vs 2-3s (20-30x faster)
# Disk usage: ~2-5 GB compressed
```

**Benefits:**
- Eliminates slow parquet reads
- Cache misses still fast (100ms)
- Better user experience for rare ISOs

### Phase 3: External Cache (Optional Scaling)

**For horizontal scaling:**
- Redis/Memcached for distributed caching
- Shared across multiple server instances
- Automatic eviction handled by Redis

---

## Configuration Parameters

### Tunable Settings

```python
# In shared_data_loader.py or config file

CACHE_MAX_ISOS = 10           # Number of ISO+tech combinations to cache
CACHE_MAX_MEMORY_GB = 3       # Memory limit (soft target)
PARQUET_FILE = 'data/hourly_profiles/atlite_grid_cell_2013.parquet'
```

### Adjusting for Your Environment

**More memory available?**
```python
CACHE_MAX_ISOS = 20           # Keep more ISOs
CACHE_MAX_MEMORY_GB = 6       # Allow more memory
```

**Memory constrained?**
```python
CACHE_MAX_ISOS = 5            # Fewer ISOs
CACHE_MAX_MEMORY_GB = 1       # Strict limit
```

**High traffic to specific regions?**
- Cache hit rate monitoring will show which ISOs to prioritize
- Consider pre-loading popular ISOs at server startup

---

## API Usage Flow

### Complete Request Flow

```
1. Frontend: User selects ISO (DEU) and capacity (10 GW)
   ↓
2. API Call: GET /generation-profile/solar-hourly/DEU?capacity_gw=10
   ↓
3. Backend: Select optimal cells (merit order by CF)
   → {cell_123: {capacity_mw: 2500, cf: 0.25, utilization: 1.0}, ...}
   ↓
4. Backend: Check cache for DEU solar shapes
   → Full hit? All cells cached → instant!
   → Partial hit? Some cached, load missing → merge
   → Cache miss? Load requested cells → cache for future
   ↓
5. Backend: Generate 8760-hour profile
   → For each cell: generation = capacity × utilization × hourly_cf_shape
   → Aggregate: total_profile = sum(all cells)
   ↓
6. API Response: [12.5, 23.1, 45.2, ...] (8760 values in MW)
   ↓
7. Frontend: Plot generation shape

8. User adjusts capacity to 15 GW → Steps 2-7 repeat
   → Cache hit! Instant response (0.01s)
```

---

## Technologies Supported

### Renewable Technologies

**Solar:** `solar_capacity_factor` column from parquet
**Wind Onshore:** `wind_capacity_factor` column from parquet  
**Wind Offshore:** `windoff_capacity_factor` column from parquet (if available)

### Data Source

**Primary:** `data/hourly_profiles/atlite_grid_cell_2013.parquet`
- Grid-cell level hourly capacity factors
- Based on Atlite weather data (2013 representative year)
- Columns: grid_cell, month, day, hour, solar_capacity_factor, wind_capacity_factor

**Fallback:** ISO-level shapes from `atlite_iso_2013.csv`
- If grid-cell data unavailable for specific cells
- One national average shape per ISO

---

## Monitoring & Debugging

### Key Metrics to Track

```python
# Log these metrics in production

cache_hits = 0           # Full cache hits (all cells found)
partial_hits = 0         # Partial hits (some cells found, loaded rest)
cache_misses = 0         # Complete misses (no cache entry)
cache_evictions = 0      # Number of ISOs evicted
avg_load_time_ms = 0     # Average parquet load time
cache_memory_mb = 0      # Current cache size

# Health checks
effective_hit_rate = (cache_hits + partial_hits) / (cache_hits + partial_hits + cache_misses)
# Target: > 85% effective hit rate

full_hit_rate = cache_hits / (cache_hits + partial_hits + cache_misses)
# Target: > 60% full hit rate
```

### Debug Commands

```python
# Inspect cache state
cache_info = shape_cache.get_cache_info()
# Returns: {iso_code: {size_mb: 140, last_accessed: timestamp}}

# Clear specific ISO
shape_cache.clear_iso('DEU')

# Clear entire cache
shape_cache.clear_all()
```

---

## Known Limitations & Future Work

### Current Limitations

1. **Cold start:** First request per ISO is slow (2-3s)
2. **Cache warming:** No pre-loading at startup
3. **No persistence:** Cache lost on server restart
4. **Single server:** Cache not shared across instances

### Planned Improvements

**Short-term:**
- [ ] Add cache warming (pre-load top 10 ISOs at startup)
- [ ] Add cache metrics endpoint for monitoring
- [ ] Optimize parquet loading with column selection

**Medium-term:**
- [ ] Implement pre-computed shape files (.npz format)
- [ ] Add compression for cached arrays
- [ ] Support custom weather years (not just 2013)

**Long-term:**
- [ ] Redis integration for distributed caching
- [ ] Real-time cache hit rate dashboard
- [ ] Auto-tuning of cache size based on traffic

---

## Related Documentation

- **Cell Selection:** See `select_cells_by_capacity()` method
- **Profile Generation:** See `generate_hourly_profile_from_cells()` method  
- **API Endpoints:** See `api_server.py` endpoints documentation
- **Data Sources:** See `2_ts_design/README.md` for Atlite integration

---

## Contact & Support

**Questions or issues?**
- Check implementation in `shared_data_loader.py`
- Review API endpoint code in `api_server.py`
- See working example: `8760_supply_demand_constructor.py`

**Performance problems?**
- Monitor cache hit rate (should be > 80%)
- Check memory usage (should be < 3 GB)
- Consider pre-computed files if load times > 3s

---

**Last reviewed:** October 30, 2025  
**Next review:** When implementing Phase 2 (pre-computed files)

