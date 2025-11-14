# Generation Profile Page - Data Flow Documentation

## Overview
This document describes the updated data flow for the Generation Profile experience. The page now auto-loads capacity for the selected ISO/year, then requests merit-order hourly profiles from the Python service for Solar and Wind (onshore). It renders both mini line charts (in GW) and two new simulator maps side-by-side, colored by utilization factor for the selected cells.

---

## API Call Flow: Sequential vs Parallel

When the generation simulator is invoked (on country/year change or manual triggers), the following calls are made:

### On Initial Load / Country/Year Change:

```
┌─────────────────────────────────────────────────────────────┐
│ TRIGGER: countryIso or formData.year changes                │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ├─► [PARALLEL] ──────────────────────────┐
                   │                                         │
                   ▼                                         ▼
        ┌──────────────────────────┐         ┌──────────────────────────┐
        │ FETCH CAPACITY (Sequential)        │ FETCH GEOJSON ZONES      │
        │                                     │ (Parallel - independent) │
        │ 1. GET /api/capacity/              │                          │
        │    capacity-by-fuel/:iso/:year     │ • GET /api/renewable/    │
        │    ↓                               │   potential/solar/:iso   │
        │ 2. Extract Solar.capacity_gw       │                          │
        │    ↓                               │ • GET /api/renewable/    │
        │ 3. GET /api/generation-profile/   │   potential/wind/:iso    │
        │    solar-hourly                    │   (onshore)             │
        │    (waits for capacity)            │                          │
        │    ↓                               │ Runs independently,      │
        │ 4. Extract Windon.capacity_gw      │ used only for map shapes │
        │    ↓                               │                          │
        │ 5. GET /api/generation-profile/   │                          │
        │    wind-hourly                     │                          │
        │    (waits for capacity)            │                          │
        └──────────────────────────┘         └──────────────────────────┘
                   │                                         │
                   └─────────────────────────────────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │ AUTO-LOAD TIMELINE CHART  │
                   │ (Parallel - independent) │
                   │                          │
                   │ POST /api/generation-    │
                   │      profile             │
                   │ (bundled profile)        │
                   └──────────────────────────┘
```

### Call Sequence Details:

**SEQUENTIAL CALLS** (within `fetchCapacityData`):
1. `capacityAPI.getCapacityByFuel(iso, year)` — **MUST complete first**
2. `generationProfileAPI.getSolarHourly(iso, year, solarCap)` — **waits for step 1**
3. `generationProfileAPI.getWindHourly(iso, year, windCap)` — **waits for step 1**

**PARALLEL CALLS** (independent, can run simultaneously):
- `fetchCapacityData()` — fetches capacity and hourly profiles
- `handleSubmit()` — fetches timeline chart data
- `renewablePotentialAPI.getSolarZones(iso)` — fetches GeoJSON shapes
- `renewablePotentialAPI.getWindZones(iso, 'onshore')` — fetches GeoJSON shapes

### Manual Actions (Go/Reload/Reset):

```
SOLAR "Go" Button:
├─► GET /api/generation-profile/solar-hourly
│   └─► Updates solarProfile + solarSelectedCells
│       └─► Chart + Map refresh together

WIND "Go" Button:
├─► GET /api/generation-profile/wind-hourly
│   └─► Updates windProfile + windSelectedCells
│       └─► Chart + Map refresh together

SOLAR/WIND "Reset" Button:
├─► Restores capacity from API
└─► Triggers same flow as "Go" (reloads chart + map)

TIMELINE "Reload" Button:
└─► POST /api/generation-profile
    └─► Updates timeline chart only
```

---

## Key Components (current)

### 1. Frontend: GenerationProfileChart.js
- **Location**: `vervestacks-dashboard/frontend/src/components/GenerationProfileChart.js`
- **Purpose**: Auto-load capacity → fetch hourly profiles (solar, wind) → render charts and simulator maps. Year dropdown resides in the left sidebar (disabled for now). No ISO input field or legacy Generate/Reset controls.
- **Key Behaviors**:
  - Auto-load timeline, solar, and wind charts on ISO/year change
  - Solar/Wind Go buttons accept manual capacity (GW)
  - Reload buttons fetch using current capacity
  - Reset restores API-provided capacity; both chart and map refresh

### 2. Frontend API Services: api.js
- **Location**: `vervestacks-dashboard/frontend/src/services/api.js`
- **Purpose**: Backend proxy clients
- **Key Features**:
  - `capacityAPI.getCapacityByFuel(iso,year)`
  - `generationProfileAPI.getSolarHourly(iso,year,capacityGw)`
  - `generationProfileAPI.getWindHourly(iso,year,capacityGw)`
  - Hourly calls use extended timeout (~120s)

### 3. Backend Routes: generationProfile.js
- **Location**: `vervestacks-dashboard/backend/routes/generationProfile.js`
- **Purpose**: Validates inputs and proxies to Python FastAPI
- **Key Functions**:
  - Routes: `/api/generation-profile/solar-hourly`, `/api/generation-profile/wind-hourly`
  - Strict validation: `isoCode`, `year`, `capacityGw`
  - Health checks to Python service

### 4. Python Service (FastAPI)
- **Location**: `vervestacks-dashboard/python-service/api_server.py`
- **Purpose**: Generates hourly profiles using merit-order cell selection
- **Endpoints**:
  - `/generation-profile/solar-hourly`
  - `/generation-profile/wind-hourly`
- **Notes**:
  - Converts NumPy arrays to lists (JSON-safe)
  - Forces renewable data reload per ISO to avoid stale cache
  - Returns `profile` (8760 GW values) and `selected_cells`

### 5. Charts & Maps
- **Charts**: Highcharts for timeline and mini charts (GW)
- **Maps**: Leaflet-based simulator maps, polygons colored by utilization factor; unmatched cells shown in light gray

---

## Data Flow Steps (current)

1. ISO and year determined by `CountryDashboard`; year dropdown is disabled
2. Frontend fetches capacities by fuel for the ISO/year
3. Frontend requests hourly profiles from Python via backend for Solar and Wind using capacityGw
4. Frontend stores: profiles (GW) + selected_cells (for maps)
5. Renders: timeline, solar/wind charts (GW), and two simulator maps colored by utilization factor
6. Go/Reload/Reset buttons refresh both charts and maps with loading overlays

---

## Request Parameters (hourly profile endpoints)

```javascript
// GET /api/generation-profile/solar-hourly?isoCode=ITA&year=2022&capacityGw=24.56
// GET /api/generation-profile/wind-hourly?isoCode=ITA&year=2022&capacityGw=12.34
```

## Response Format (hourly profile endpoints)

```javascript
{
  success: true,
  profile: [/* 8760 values in GW */],
  selected_cells: {
    "cell_id": {
      "utilization_factor": 0.42,
      "capacity_mw": 123.0,
      // ... other metrics
    }
  }
}
```

---

## Error Handling

- **Validation Errors**: 400 with details (backend routes)
- **Python errors**: 500 with explicit message from Python service (no fallbacks)
- **Timeouts**: Hourly calls use ~120s timeout end-to-end
- **Unavailable data**: UI shows targeted error messages per card/map

---

## Notes

- Capacity is sourced from `/capacity-by-fuel` and passed as `capacityGw` to hourly profile endpoints
- Profiles are displayed in GW across charts
- Two simulator maps (Solar/Wind) visualize `selected_cells` joined to GeoJSON zones, colored by utilization factor; unmatched cells are light gray
- Year dropdown remains disabled; ISO change resets charts/maps and shows loading overlays

