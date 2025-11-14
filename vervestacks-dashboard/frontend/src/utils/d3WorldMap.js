import * as d3 from "d3";
import * as d3Geo from "d3-geo";
import * as d3Zoom from "d3-zoom";

/**
 * D3 World Map Utility
 *
 * Centralizes creation and update of a D3-based world map inside an SVG element.
 * Preserves zoom state on resize and avoids duplicating DOM elements like tooltips.
 */

const defaultColors = {
  ocean: "#D2DFFF",
  country: "#C5D0EF",
  border: "#D2DFFF",
  hover: "#8B5CF6",
  selected: "#A855F7",
};

function debounce(fn, wait) {
  let t;
  return function debounced(...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}

export function createWorldMap(svgElement, geojson, options = {}) {
  const {
    onCountrySelect,
    selectedCountryName,
    colors = defaultColors,
    zoomOptions = { extent: [0.5, 8], initialScale: 0.87 },
    debounceMs = 150,
  } = options;

  if (!svgElement || !geojson) {
    throw new Error("createWorldMap: svgElement and geojson are required");
  }

  const svg = d3.select(svgElement);
  svg.selectAll("*").remove();

  const width = svgElement.clientWidth;
  const height = svgElement.clientHeight;

  const projection = d3Geo.geoMercator().fitSize([width, height], geojson);
  const path = d3Geo.geoPath().projection(projection);

  // Ocean background
  svg
    .append("rect")
    .attr("width", width)
    .attr("height", height)
    .attr("fill", colors.ocean)
    .attr("class", "ocean-background");

  // Gradients/defs (one-time per render)
  const defs = svg.append("defs");
  const hoverGradient = defs
    .append("linearGradient")
    .attr("id", "hoverGradient")
    .attr("gradientUnits", "objectBoundingBox")
    .attr("gradientTransform", "rotate(45)");
  hoverGradient.append("stop").attr("offset", "0%").attr("stop-color", "#F8B26A");
  hoverGradient.append("stop").attr("offset", "100%").attr("stop-color", "#FC8462");

  // Persistent tooltip (single instance)
  d3.selectAll("body > div.tooltip").remove();
  const tooltip = d3
    .select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0)
    .style("position", "absolute")
    .style("background", "rgba(0, 0, 0, 0.8)")
    .style("color", "white")
    .style("padding", "8px 12px")
    .style("border-radius", "6px")
    .style("font-size", "14px")
    .style("font-weight", "500")
    .style("pointer-events", "none")
    .style("z-index", "1000")
    .style("box-shadow", "0 4px 6px rgba(0, 0, 0, 0.1)");

  // Map group
  const mapGroup = svg.append("g").attr("class", "map-group");

  // Zoom behavior
  const zoom = d3Zoom
    .zoom()
    .scaleExtent(zoomOptions.extent || [0.5, 8])
    .on("zoom", (event) => {
      mapGroup.attr("transform", event.transform);
    });
  svg.call(zoom);

  // Initial zoom
  if (zoomOptions.initialScale) {
    svg.call(zoom.transform, d3Zoom.zoomIdentity.scale(zoomOptions.initialScale));
  }

  // Countries
  const countriesSel = mapGroup
    .selectAll(".country")
    .data(geojson.features)
    .enter()
    .append("path")
    .attr("class", "country")
    .attr("d", path)
    .attr("fill", colors.country)
    .attr("stroke", colors.border)
    .attr("stroke-width", 0.5)
    .style("cursor", "pointer")
    .on("mouseenter", function (event, d) {
      const countryName = d.properties?.name;
      const isSelected =
        selectedCountryName &&
        countryName?.toLowerCase() === selectedCountryName.toLowerCase();
      if (!isSelected) {
        d3.select(this).attr("fill", "url(#hoverGradient)").style("opacity", 1);
      }
      tooltip
        .style("opacity", 1)
        .html(countryName || "Unknown Country")
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 10 + "px");
    })
    .on("mouseleave", function (event, d) {
      const countryName = d.properties?.name;
      const isSelected =
        selectedCountryName &&
        countryName?.toLowerCase() === selectedCountryName.toLowerCase();
      if (!isSelected) {
        d3.select(this).attr("fill", colors.country).style("opacity", 1);
      }
      tooltip.style("opacity", 0);
    })
    .on("click", function (event, d) {
      if (!onCountrySelect) return;
      const countryName = d.properties?.name;
      onCountrySelect(countryName);
    });

  // Highlight selection if provided
  if (selectedCountryName) {
    countriesSel
      .filter((d) => d.properties?.name?.toLowerCase() === selectedCountryName.toLowerCase())
      .attr("fill", "url(#hoverGradient)") // Use gradient for selected country
      .style("opacity", 1);
  }

  function getZoomTransform() {
    return d3.zoomTransform(svgElement);
  }

  function setZoomTransform(transform) {
    if (!transform) return;
    svg.call(zoom.transform, transform);
  }

  function updateSize() {
    const prevTransform = getZoomTransform();
    const newWidth = svgElement.clientWidth;
    const newHeight = svgElement.clientHeight;

    // Update projection and re-path without clearing groups/handlers
    const newProjection = d3Geo.geoMercator().fitSize([newWidth, newHeight], geojson);
    
    const newPath = d3Geo.geoPath().projection(newProjection);

    svg.select("rect.ocean-background")
      .attr("width", newWidth)
      .attr("height", newHeight)
      .attr("fill", colors.ocean);

    mapGroup.selectAll("path.country").attr("d", newPath);

    // Reapply previous zoom transform to preserve state
    setZoomTransform(prevTransform);
  }

  const debouncedUpdateSize = debounce(updateSize, debounceMs);

  function setSelectedCountry(name) {
    mapGroup
      .selectAll("path.country")
      .attr("fill", (d) => {
        const nm = d.properties?.name;
        if (name && nm && nm.toLowerCase() === name.toLowerCase()) {
          return "url(#hoverGradient)"; // Use gradient for selected country
        }
        return colors.country;
      });
  }

  function centerOnCountry(name) {
    if (!name) return;
    const feature = geojson.features.find((f) => {
      const countryName = f.properties?.name;
      return countryName?.toLowerCase() === name.toLowerCase();
    });
    if (!feature) return;

    const currentWidth = svgElement.clientWidth;
    const currentHeight = svgElement.clientHeight;
    const currentProjection = d3Geo.geoMercator().fitSize([currentWidth, currentHeight], geojson);
    
    const currentPath = d3Geo.geoPath().projection(currentProjection);

    const [[x0, y0], [x1, y1]] = currentPath.bounds(feature);
    const dx = x1 - x0;
    const dy = y1 - y0;
    const x = (x0 + x1) / 2;
    const y = (y0 + y1) / 2;
    const scale = Math.max(1, Math.min(8, 0.9 / Math.max(dx / currentWidth, dy / currentHeight)));
    const translate = [currentWidth / 2 - scale * x, currentHeight / 2 - scale * y];

    svg
      .transition()
      .duration(750)
      .call(zoom.transform, d3Zoom.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
  }

  function destroy() {
    // Remove tooltip and handlers
    d3.selectAll("body > div.tooltip").remove();
  }

  function resetView() {
    // Reset zoom to initial scale
    if (zoomOptions.initialScale) {
      svg.call(zoom.transform, d3Zoom.zoomIdentity.scale(zoomOptions.initialScale));
    }
    
    // Clear any selected country
    setSelectedCountry(null);
  }

  // Attach window resize listener (the caller may manage it as well)
  const onResize = () => debouncedUpdateSize();
  window.addEventListener("resize", onResize);

  return {
    updateSize,
    debouncedUpdateSize,
    setSelectedCountry,
    centerOnCountry,
    getZoomTransform,
    setZoomTransform,
    resetView,
    destroy: () => {
      window.removeEventListener("resize", onResize);
      destroy();
    },
  };
}

const d3WorldMap = { createWorldMap };
export default d3WorldMap;


