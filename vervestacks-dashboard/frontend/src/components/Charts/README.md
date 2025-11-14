# Chart Components for VerveStacks Dashboard

This directory contains chart components that display energy data from the VerveStacks Python service.

## Components

### GenerationChart
Displays electricity generation data over time by fuel type using stacked area charts.

**Features:**
- Stacked area chart showing generation by fuel type
- Time series from 2000-2022
- Interactive tooltips with generation values in TWh
- Consistent fuel type color coding
- Responsive design with loading and error states

**Usage:**
```jsx
import GenerationChart from '../components/Charts/GenerationChart';

<GenerationChart countryIso="USA" year={2022} />
```

### CapacityChart
Displays installed capacity data over time by fuel type using line charts.

**Features:**
- Line chart showing capacity evolution by fuel type
- Time series from 2000-2022
- Interactive tooltips with capacity values in GW
- Consistent fuel type color coding
- Responsive design with loading and error states

**Usage:**
```jsx
import CapacityChart from '../components/Charts/CapacityChart';

<CapacityChart countryIso="USA" year={2022} />
```

### EnergySummary
Displays key energy metrics and year-over-year changes in card format.

**Features:**
- Summary cards for each fuel type
- Generation and capacity metrics
- Year-over-year percentage changes
- Color-coded fuel type indicators
- Responsive grid layout

**Usage:**
```jsx
import EnergySummary from '../components/Charts/EnergySummary';

<EnergySummary countryIso="USA" year={2022} />
```

## Data Source

All components use the `/api/overview/capacity-utilization/{iso_code}` endpoint which provides:

```json
{
  "success": true,
  "data": {
    "iso_code": "USA",
    "years": [2000, 2001, ..., 2022],
    "fuel_types": ["coal", "gas", "hydro", "nuclear", "oil", "solar", "wind"],
    "generation_chart": {
      "coal": [1966.27, 1903.96, ...],
      "gas": [614.99, 639.13, ...],
      // ... other fuel types
    },
    "capacity_chart": {
      "coal": [334.24, 335.32, ...],
      "gas": [161.54, 199.67, ...],
      // ... other fuel types
    }
  }
}
```

## Fuel Type Colors

Consistent color coding across all charts:
- **Coal**: #374151 (Gray)
- **Gas**: #3b82f6 (Blue)
- **Hydro**: #06b6d4 (Cyan)
- **Nuclear**: #f59e0b (Yellow)
- **Oil**: #dc2626 (Red)
- **Solar**: #fbbf24 (Yellow)
- **Wind**: #10b981 (Green)

## Error Handling

All components include comprehensive error handling:
- Loading states with spinners
- Error states with retry buttons
- User-friendly error messages
- Graceful fallbacks for missing data

## Dependencies

- **Highcharts**: Professional charting library
- **React**: Component framework
- **Tailwind CSS**: Styling and design system
- **Lucide React**: Icons

## Design System Compliance

Components follow the VerveStacks design system:
- Use established color palette and gradients
- Follow consistent spacing and typography
- Implement proper loading and error states
- Use design system classes (.btn-primary, .card, etc.)
