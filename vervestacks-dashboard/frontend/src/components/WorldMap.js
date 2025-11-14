import React, {
  useEffect,
  useRef,
  useState,
  useMemo,
  useCallback,
} from "react";
import * as d3 from "d3";
import * as topojson from "topojson-client";
import { createWorldMap } from "../utils/d3WorldMap";

const WorldMap = ({ onCountrySelect, selectedCountry, countries = [], controllerRef }) => {
  const svgRef = useRef();
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Simple color scheme - memoized to prevent re-renders
  const colors = useMemo(
    () => ({
      ocean: "#D2DFFF",
      country: "#C5D0EF",
      border: "#D2DFFF",
      hover: "#8B5CF6",
      selected: "#A855F7",
    }),
    []
  );

  // Function to center and zoom on a specific country - now uses controller
  const centerOnCountry = useCallback(
    (country) => {
      if (!country || !controllerRef.current) return;
      
      // Use the controller's centerOnCountry method
      controllerRef.current.centerOnCountry(country.name);
    },
    [controllerRef]
  );

  // Expose function globally for debugging
  useEffect(() => {
    window.debugCenterOnCountry = centerOnCountry;
    window.debugMapData = mapData;
    // Add function to get current zoom level
    window.getCurrentZoomLevel = () => {
      if (controllerRef.current) {
        const currentTransform = controllerRef.current.getZoomTransform();
        console.log(`Current zoom level: ${currentTransform.k.toFixed(2)}x`);
        return currentTransform.k;
      }
      return 1.0;
    };
  }, [centerOnCountry, mapData, controllerRef]);

  // Load map data
  useEffect(() => {
    const loadMapData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"
        );

        if (!response.ok) {
          throw new Error(`Failed to load map data: ${response.status}`);
        }

        const data = await response.json();

        // Convert TopoJSON to GeoJSON and filter out Antarctica
        const countries = topojson.feature(data, data.objects.countries);
        
        const filteredData = {
          ...countries,
          features:
            countries.features?.filter((feature) => {
              const name = feature.properties?.name;
              // Filter out Antarctica
              if (name?.toLowerCase().includes("antarctica")) {
                return false;
              }

              return true;
            }) || [],
        };

        setMapData(filteredData);
        setLoading(false);
      } catch (err) {
        console.error("Error loading map data:", err);
        setError(err.message);
        setLoading(false);
      }
    };

    loadMapData();
  }, []);

  // Center on country when selectedCountry changes (through controller)
  useEffect(() => {
    if (selectedCountry && controllerRef.current) {
      controllerRef.current.setSelectedCountry(selectedCountry.name);
      controllerRef.current.centerOnCountry(selectedCountry.name);
    }
  }, [selectedCountry, controllerRef]);

  // Render map using the shared utility
  useEffect(() => {
    if (!mapData || !svgRef.current) return;

    // Map function expects callback with country name; translate to matching object
    controllerRef.current = createWorldMap(svgRef.current, mapData, {
      onCountrySelect: (countryName) => {
        if (!onCountrySelect) return;
        
        // Create a mapping of common country name variations
        const countryNameMap = {
          'usa': 'United States',
          'united states': 'United States',
          'united states of america': 'United States',
          'us': 'United States',
          'america': 'United States',
          'uk': 'United Kingdom',
          'united kingdom': 'United Kingdom',
          'great britain': 'United Kingdom',
          'britain': 'United Kingdom',
          'uae': 'United Arab Emirates',
          'united arab emirates': 'United Arab Emirates',
          'south korea': 'South Korea',
          'north korea': 'North Korea',
          'czech republic': 'Czech Republic',
          'czechia': 'Czech Republic',
          'slovakia': 'Slovakia',
          'slovak republic': 'Slovakia',
          'russia': 'Russia',
          'russian federation': 'Russia',
          'iran': 'Iran',
          'islamic republic of iran': 'Iran',
          'china': 'China',
          'people\'s republic of china': 'China',
          'prc': 'China',
          'taiwan': 'Taiwan',
          'republic of china': 'Taiwan',
          'roc': 'Taiwan',
          'vietnam': 'Vietnam',
          'viet nam': 'Vietnam',
          'socialist republic of vietnam': 'Vietnam',
          'philippines': 'Philippines',
          'republic of the philippines': 'Philippines',
          'south africa': 'South Africa',
          'republic of south africa': 'South Africa',
          'congo': 'Congo',
          'democratic republic of the congo': 'Congo',
          'drc': 'Congo',
          'central african republic': 'Central African Republic',
          'car': 'Central African Republic',
          'dominican republic': 'Dominican Republic',
          'dr': 'Dominican Republic',
          'costa rica': 'Costa Rica',
          'el salvador': 'El Salvador',
          'trinidad and tobago': 'Trinidad and Tobago',
          'trinidad & tobago': 'Trinidad and Tobago',
          'antigua and barbuda': 'Antigua and Barbuda',
          'antigua & barbuda': 'Antigua and Barbuda',
          'saint kitts and nevis': 'Saint Kitts and Nevis',
          'st. kitts and nevis': 'Saint Kitts and Nevis',
          'saint vincent and the grenadines': 'Saint Vincent and the Grenadines',
          'st. vincent and the grenadines': 'Saint Vincent and the Grenadines',
          'saint lucia': 'Saint Lucia',
          'st. lucia': 'Saint Lucia',
          'bosnia and herzegovina': 'Bosnia and Herzegovina',
          'bosnia & herzegovina': 'Bosnia and Herzegovina',
          'macedonia': 'North Macedonia',
          'north macedonia': 'North Macedonia',
          'moldova': 'Moldova',
          'republic of moldova': 'Moldova',
          'papua new guinea': 'Papua New Guinea',
          'new zealand': 'New Zealand',
          'sri lanka': 'Sri Lanka',
          'democratic socialist republic of sri lanka': 'Sri Lanka',
          'brunei': 'Brunei',
          'brunei darussalam': 'Brunei',
          'myanmar': 'Myanmar',
          'burma': 'Myanmar',
          'republic of the union of myanmar': 'Myanmar',
          'laos': 'Laos',
          'lao people\'s democratic republic': 'Laos',
          'cambodia': 'Cambodia',
          'kingdom of cambodia': 'Cambodia',
          'thailand': 'Thailand',
          'kingdom of thailand': 'Thailand',
          'malaysia': 'Malaysia',
          'indonesia': 'Indonesia',
          'republic of indonesia': 'Indonesia',
          'singapore': 'Singapore',
          'republic of singapore': 'Singapore',
          'bangladesh': 'Bangladesh',
          'people\'s republic of bangladesh': 'Bangladesh',
          'nepal': 'Nepal',
          'federal democratic republic of nepal': 'Nepal',
          'bhutan': 'Bhutan',
          'kingdom of bhutan': 'Bhutan',
          'afghanistan': 'Afghanistan',
          'islamic emirate of afghanistan': 'Afghanistan',
          'pakistan': 'Pakistan',
          'islamic republic of pakistan': 'Pakistan',
          'india': 'India',
          'republic of india': 'India',
          'maldives': 'Maldives',
          'republic of maldives': 'Maldives',
          'kyrgyzstan': 'Kyrgyzstan',
          'kyrgyz republic': 'Kyrgyzstan',
          'tajikistan': 'Tajikistan',
          'republic of tajikistan': 'Tajikistan',
          'turkmenistan': 'Turkmenistan',
          'uzbekistan': 'Uzbekistan',
          'republic of uzbekistan': 'Uzbekistan',
          'kazakhstan': 'Kazakhstan',
          'republic of kazakhstan': 'Kazakhstan',
          'mongolia': 'Mongolia',
          'japan': 'Japan',
          'republic of korea': 'South Korea',
          'rok': 'South Korea',
          'democratic people\'s republic of korea': 'North Korea',
          'dprk': 'North Korea',
          'hong kong': 'Hong Kong',
          'macau': 'Macau',
          'macao': 'Macau',
          'special administrative region of macau': 'Macau',
          'special administrative region of macao': 'Macau'
        };
        
        // Normalize the country name for matching
        const normalizedMapName = countryNameMap[countryName?.toLowerCase()];
        const searchName = normalizedMapName || countryName;
        
        const match = countries.find(
          (c) => c.name?.toLowerCase() === searchName?.toLowerCase()
        );
        
        if (match) onCountrySelect(match);
      },
      selectedCountryName: selectedCountry?.name,
      colors,
      zoomOptions: { extent: [0.5, 8], initialScale: 0.87 },
      debounceMs: 150,
    });

    // If a country is already selected (e.g., via CountryList) before controller ready,
    // apply selection and center/zoom now.
    if (selectedCountry?.name && controllerRef.current) {
      controllerRef.current.setSelectedCountry(selectedCountry.name);
      controllerRef.current.centerOnCountry(selectedCountry.name);
    }

    return () => {
      if (controllerRef.current) {
        controllerRef.current.destroy();
        controllerRef.current = null;
      }
    };
  }, [mapData, colors, countries, onCountrySelect, selectedCountry?.name, controllerRef]);

  // Resize updates are handled by the controller created in the utility

  // Cleanup tooltip on unmount
  useEffect(() => {
    return () => {
      d3.selectAll(".tooltip").remove();
    };
  }, []);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading world map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="mx-auto mb-4">
            <svg
              className="h-12 w-12 text-red-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 19.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          <p className="text-red-600 mb-2">Failed to load map data</p>
          <p className="text-gray-600 text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ background: colors.ocean }}
      />
    </div>
  );
};

export default WorldMap;
