"""
Quick Test Script for Grid Cell Profile Generation
===================================================

Tests the complete flow:
1. Select cells by capacity (merit order)
2. Generate 8760-hour profile from selected cells
3. Check cache performance

Run from project root:
    python 2_ts_design/test_grid_cell_profiles.py
"""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / '2_ts_design' / 'scripts'))

# Import modules
import importlib.util
script_path = project_root / '2_ts_design' / 'scripts' / '8760_supply_demand_constructor.py'
spec = importlib.util.spec_from_file_location("supply_module", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

from shared_data_loader import get_shape_cache

def test_basic_flow(iso_code='DEU', capacity_gw=10.0):
    """Test complete flow: select cells → generate profile"""
    
    print("=" * 60)
    print(f"🧪 Testing Grid Cell Profile Generation")
    print(f"ISO: {iso_code}, Target Capacity: {capacity_gw} GW")
    print("=" * 60)
    
    # Initialize constructor
    data_path = str(project_root / 'data' / '')
    constructor = module.Supply8760Constructor(data_path)
    
    # Step 1: Select cells
    print("\n📋 Step 1: Loading renewable data and selecting cells...")
    try:
        solar_cells, wind_cells, windoff_cells, _, _ = constructor._load_renewable_data(iso_code, force_reload=False)
        print(f"✅ Loaded {len(solar_cells)} solar cells for {iso_code}")
    except Exception as e:
        print(f"❌ Error loading renewable data: {e}")
        return False
    
    print(f"\n🎯 Selecting optimal cells for {capacity_gw} GW...")
    try:
        selected_cells = constructor.select_cells_by_capacity(
            solar_cells,
            target_capacity_gw=capacity_gw,
            technology='solar'
        )
        print(f"✅ Selected {len(selected_cells)} cells")
        
        # Show first 3 cells
        print("\n📊 Sample of selected cells:")
        for i, (cell_id, info) in enumerate(list(selected_cells.items())[:3]):
            print(f"  {cell_id}: {info['capacity_mw']:.1f} MW, CF={info['capacity_factor']:.3f}, Util={info['utilization_ratio']:.3f}")
        
    except Exception as e:
        print(f"❌ Error selecting cells: {e}")
        return False
    
    # Step 2: Generate profile
    print(f"\n⚡ Step 2: Generating 8760-hour profile...")
    try:
        hourly_profile = constructor.generate_hourly_profile_from_cells(
            selected_cells, iso_code, 'solar'
        )
        
        print(f"✅ Generated profile: {len(hourly_profile)} hours")
        print(f"   Min: {min(hourly_profile):.2f} MW")
        print(f"   Max: {max(hourly_profile):.2f} MW")
        print(f"   Avg: {sum(hourly_profile)/len(hourly_profile):.2f} MW")
        
        # Show sample hours
        print(f"\n📈 Sample hours:")
        sample_hours = [0, 2000, 4000, 6000, 8000]
        for hour in sample_hours:
            print(f"   Hour {hour}: {hourly_profile[hour]:.2f} MW")
            
    except Exception as e:
        print(f"❌ Error generating profile: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Check cache stats
    print(f"\n📊 Step 3: Cache Performance")
    try:
        cache = get_shape_cache(data_dir=data_path)
        stats = cache.get_cache_stats()
        info = cache.get_cache_info()
        
        print(f"   Cache hits: {stats['hits']}")
        print(f"   Cache misses: {stats['misses']}")
        print(f"   Hit rate: {stats['hit_rate_percent']:.1f}%")
        print(f"   Cached ISOs: {info['cache_size']}/{info['max_size']}")
        
        for iso_key, iso_info in info['cached_isos'].items():
            print(f"   - {iso_key}: {iso_info['num_cells']} cells, {iso_info['memory_mb']:.1f} MB")
            
    except Exception as e:
        print(f"⚠️  Could not get cache stats: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)
    return True


def test_cache_speed(iso_code='DEU', capacity_gw=10.0):
    """Test cache speed improvement"""
    import time
    
    print("\n" + "=" * 60)
    print("⚡ Testing Cache Speed Improvement")
    print("=" * 60)
    
    data_path = str(project_root / 'data' / '')
    constructor = module.Supply8760Constructor(data_path)
    
    # Load and select cells
    solar_cells, _, _, _, _ = constructor._load_renewable_data(iso_code, force_reload=False)
    selected_cells = constructor.select_cells_by_capacity(solar_cells, capacity_gw, 'solar')
    
    # First call (cache miss)
    print(f"\n🔴 First call (cache miss expected):")
    start = time.time()
    profile1 = constructor.generate_hourly_profile_from_cells(selected_cells, iso_code, 'solar')
    time1 = time.time() - start
    print(f"   Time: {time1:.3f} seconds")
    
    # Second call (cache hit)
    print(f"\n🟢 Second call (cache hit expected):")
    start = time.time()
    profile2 = constructor.generate_hourly_profile_from_cells(selected_cells, iso_code, 'solar')
    time2 = time.time() - start
    print(f"   Time: {time2:.3f} seconds")
    
    # Calculate speedup
    speedup = time1 / time2 if time2 > 0 else 0
    print(f"\n🚀 Speedup: {speedup:.1f}x faster")
    
    # Verify profiles are identical
    if profile1 == profile2:
        print(f"✅ Profiles are identical")
    else:
        print(f"⚠️  Profiles differ!")
    
    print("=" * 60)


if __name__ == "__main__":
    # Run basic test
    success = test_basic_flow(iso_code='DEU', capacity_gw=10.0)
    
    if success:
        # Run speed test
        test_cache_speed(iso_code='DEU', capacity_gw=10.0)
    
    print("\n✨ All tests complete!")

