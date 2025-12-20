import io
import logging
from typing import Any, Callable, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Try to import staticmap for local tile rendering
try:
    import staticmap

    STATICMAP_AVAILABLE = True
except ImportError:
    STATICMAP_AVAILABLE = False
    logger.warning("staticmap not installed.")


def decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """
    Decode a polyline string into a list of (longitude, latitude) tuples.

    OpenRouteService uses encoded polylines (Google Polyline Algorithm)
    to compress route coordinates. This function decodes them.

    Args:
        encoded: Encoded polyline string
        precision: Coordinate precision (ORS uses 5)

    Returns:
        list of (lon, lat) tuples
    """
    coordinates = []
    index = 0
    lat = 0
    lon = 0

    while index < len(encoded):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break

        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break

        dlon = ~(result >> 1) if result & 1 else result >> 1
        lon += dlon

        # Convert to decimal degrees
        coordinates.append(
            (
                lon / (10**precision),  # longitude first for GeoJSON
                lat / (10**precision),  # latitude second
            )
        )

    return coordinates


# Type alias for progress callback
ProgressCallback = Callable[[int, str], None]


class MapGenerator:
    """
    Generate accurate route maps using OpenStreetMap tiles with full road geometry
    from OpenRouteService.

    Features:
    - Full route geometry (all road points, not simplified)
    - Encoded polyline decoding support
    - Multi-segment routes with different colors
    - Direction arrows showing route flow
    - Rest and fuel stop markers along route
    - Distance and duration info
    - Progress callback support for async operations
    """

    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800

    # Marker colors (RGB tuples for PIL, hex for staticmap)
    MARKER_COLORS = {
        "start": {"rgb": (34, 139, 34), "hex": "#228B22"},  # Forest green
        "pickup": {"rgb": (30, 144, 255), "hex": "#1E90FF"},  # Dodger blue
        "dropoff": {"rgb": (220, 20, 60), "hex": "#DC143C"},  # Crimson
        "rest": {"rgb": (148, 0, 211), "hex": "#9400D3"},  # Purple
        "fuel": {"rgb": (255, 140, 0), "hex": "#FF8C00"},  # Dark orange
        "break": {"rgb": (255, 215, 0), "hex": "#FFD700"},  # Gold
    }

    # Route segment colors for multi-leg trips
    SEGMENT_COLORS = [
        "#3388ff",  # Blue (primary)
        "#ff6b6b",  # Red
        "#4ecdc4",  # Teal
        "#45b7d1",  # Light blue
        "#96ceb4",  # Sage green
    ]

    ROUTE_WIDTH = 4
    MARKER_RADIUS = 14
    SMALL_MARKER_RADIUS = 8

    def generate_route_map(
        self,
        coordinates: list[dict[str, float]],
        segments: list[dict[str, Any]],
        geometry: Optional[dict[str, Any]] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        route_data: Optional[dict[str, Any]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bytes:
        """
        Generate a route map showing the actual road route and stops.

        Args:
            coordinates: list of {lat, lon, name} dicts for waypoints
            segments: list of trip segments with types and locations
            geometry: OpenRouteService GeoJSON geometry with route coordinates
            width: Image width in pixels
            height: Image height in pixels
            route_data: Full route data from ORS (for additional details)
            progress_callback: Optional callback for progress updates (progress: int, message: str)

        Returns:
            PNG image as bytes
        """

        # Helper to safely call progress callback
        def update_progress(progress: int, message: str = "") -> None:
            if progress_callback:
                try:
                    progress_callback(progress, message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        update_progress(0, "Starting map generation")

        # Decode geometry if it's an encoded polyline string
        update_progress(10, "Processing route geometry")
        decoded_geometry = self._process_geometry(geometry)

        update_progress(20, "Checking map renderer availability")

        if not STATICMAP_AVAILABLE:
            logger.warning("staticmap not available, using fallback")
            update_progress(30, "Using fallback renderer")
            return self._generate_fallback_map(
                coordinates, segments, decoded_geometry, width, height, update_progress
            )

        try:
            return self._generate_with_staticmap(
                coordinates,
                segments,
                decoded_geometry,
                width,
                height,
                route_data,
                update_progress,
            )
        except Exception as e:
            logger.error(f"Error generating map: {e}", exc_info=True)
            update_progress(30, "Falling back to basic renderer")
            return self._generate_fallback_map(
                coordinates, segments, decoded_geometry, width, height, update_progress
            )

    def _process_geometry(
        self, geometry: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """
        Process geometry - decode if encoded polyline, otherwise return as-is.
        """
        if geometry is None:
            return None

        # If it's already a GeoJSON geometry with coordinates
        if isinstance(geometry, dict) and geometry.get("coordinates"):
            coords = geometry["coordinates"]
            # Validate coordinates format
            if coords and isinstance(coords[0], (list, tuple)) and len(coords[0]) >= 2:
                logger.info(f"Using GeoJSON geometry with {len(coords)} points")
                return geometry

        # If it's an encoded polyline string
        if isinstance(geometry, str):
            try:
                decoded = decode_polyline(geometry)
                logger.info(f"Decoded polyline with {len(decoded)} points")
                return {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lon, lat in decoded],
                }
            except Exception as e:
                logger.error(f"Failed to decode polyline: {e}")
                return None

        # Check if geometry contains encoded polyline
        if isinstance(geometry, dict):
            encoded = geometry.get("encoded") or geometry.get("polyline")
            if encoded and isinstance(encoded, str):
                try:
                    decoded = decode_polyline(encoded)
                    logger.info(f"Decoded embedded polyline with {len(decoded)} points")
                    return {
                        "type": "LineString",
                        "coordinates": [[lon, lat] for lon, lat in decoded],
                    }
                except Exception as e:
                    logger.error(f"Failed to decode embedded polyline: {e}")

        return geometry

    def _generate_with_staticmap(
        self,
        coordinates: list[dict[str, float]],
        segments: list[dict[str, Any]],
        geometry: Optional[dict[str, Any]],
        width: int,
        height: int,
        route_data: Optional[dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> bytes:
        """Generate map using staticmap library with full route geometry."""

        def update_progress(progress: int, message: str = "") -> None:
            if progress_callback:
                try:
                    progress_callback(progress, message)
                except Exception:
                    pass

        update_progress(25, "Initializing map renderer")

        # Create static map with OSM tiles
        m = staticmap.StaticMap(
            width,
            height,
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            tile_size=256,
        )

        update_progress(30, "Drawing route line")

        # Draw the route
        route_drawn = False
        route_points = 0

        if geometry and geometry.get("coordinates"):
            route_coords = geometry["coordinates"]
            route_points = len(route_coords)

            if route_points >= 2:
                # Convert to staticmap format: list of (lon, lat) tuples
                line_coords = [(coord[0], coord[1]) for coord in route_coords]

                # Draw route outline (darker, wider) for better visibility
                outline = staticmap.Line(
                    line_coords,
                    "#1a5276",  # Dark blue outline
                    self.ROUTE_WIDTH + 2,
                )
                m.add_line(outline)

                # Draw main route line
                route_line = staticmap.Line(
                    line_coords,
                    self.SEGMENT_COLORS[0],
                    self.ROUTE_WIDTH,
                )
                m.add_line(route_line)
                route_drawn = True

                logger.info(f"Drawing accurate route with {route_points} road points")

                # Add direction arrows along the route
                self._add_direction_markers(m, line_coords)

        update_progress(40, "Processing waypoints")

        # Fallback: straight lines between waypoints if no geometry
        if not route_drawn and len(coordinates) >= 2:
            logger.warning(
                "No route geometry, drawing straight lines between waypoints"
            )
            line_coords = [(c["lon"], c["lat"]) for c in coordinates]
            fallback_line = staticmap.Line(
                line_coords,
                "#999999",
                2,
            )
            m.add_line(fallback_line)

        # Extract all markers including intermediate stops
        markers = self._extract_all_markers(coordinates, segments, geometry)

        update_progress(50, f"Adding {len(markers)} markers")

        # Add markers - small ones first, then main waypoints on top
        for i, marker in enumerate(sorted(markers, key=lambda m: m.get("priority", 0))):
            color = self.MARKER_COLORS.get(marker["type"], {}).get("hex", "#808080")
            radius = marker.get("radius", self.MARKER_RADIUS)

            # Add white outline for visibility
            outline_marker = staticmap.CircleMarker(
                (marker["lon"], marker["lat"]),
                "white",
                radius + 3,
            )
            m.add_marker(outline_marker)

            # Add colored marker
            circle = staticmap.CircleMarker(
                (marker["lon"], marker["lat"]),
                color,
                radius,
            )
            m.add_marker(circle)

            # Update progress periodically
            if i % 5 == 0:
                progress = 50 + int((i / max(len(markers), 1)) * 20)
                update_progress(progress, f"Adding marker {i + 1}/{len(markers)}")

        update_progress(70, "Fetching map tiles and rendering")

        # Render the map
        try:
            image = m.render()
        except Exception as e:
            logger.error(f"Failed to render map: {e}")
            raise

        update_progress(80, "Adding overlays")

        # Add overlays
        image = self._add_legend(image, markers, segments)
        image = self._add_route_info(image, coordinates, geometry, route_data)
        image = self._add_waypoint_labels(image, markers, m)

        update_progress(90, "Encoding image")

        # Convert to bytes
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        buf.seek(0)

        update_progress(100, "Map generation complete")

        logger.info(
            f"Generated route map: {route_points} points, {len(markers)} markers"
        )
        return buf.getvalue()

    def _add_direction_markers(
        self,
        m: "staticmap.StaticMap",
        line_coords: list[tuple[float, float]],
        interval: int = 50,
    ) -> None:
        """
        Add small direction indicators along the route.

        Args:
            m: StaticMap instance
            line_coords: Route coordinates
            interval: Add marker every N points
        """
        if len(line_coords) < interval * 2:
            return

        # Add small markers at intervals to show direction
        for i in range(interval, len(line_coords) - interval, interval):
            coord = line_coords[i]

            # Small dot to indicate route direction
            dot = staticmap.CircleMarker(
                coord,
                "#ffffff",
                3,
            )
            m.add_marker(dot)

    def _extract_all_markers(
        self,
        coordinates: list[dict[str, float]],
        segments: list[dict[str, Any]],
        geometry: Optional[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract all markers including waypoints and intermediate stops.
        """
        markers = []

        # Main waypoints (higher priority, larger markers)
        for i, coord in enumerate(coordinates):
            if i == 0:
                marker_type = "start"
            elif i == len(coordinates) - 1:
                marker_type = "dropoff"
            else:
                marker_type = "pickup"

            markers.append(
                {
                    "lat": coord["lat"],
                    "lon": coord["lon"],
                    "type": marker_type,
                    "label": coord.get("name", f"Point {i + 1}"),
                    "radius": self.MARKER_RADIUS,
                    "priority": 10,  # High priority - render on top
                }
            )

        # Extract intermediate stops from segments
        route_coords = []
        if geometry and geometry.get("coordinates"):
            route_coords = geometry["coordinates"]

        total_route_points = len(route_coords)
        segment_index = 0

        for seg in segments:
            seg_type = seg.get("type", "")

            if seg_type in ["rest", "fuel", "break"]:
                seg_lat = seg.get("lat") or seg.get("latitude")
                seg_lon = seg.get("lon") or seg.get("longitude")

                if seg_lat and seg_lon:
                    markers.append(
                        {
                            "lat": seg_lat,
                            "lon": seg_lon,
                            "type": seg_type,
                            "label": seg.get("location", seg_type.capitalize()),
                            "radius": self.SMALL_MARKER_RADIUS,
                            "priority": 5,
                        }
                    )
                elif total_route_points > 0:
                    segment_index += 1
                    est_position = min(
                        int(total_route_points * segment_index / (len(segments) + 1)),
                        total_route_points - 1,
                    )
                    est_coord = route_coords[est_position]

                    markers.append(
                        {
                            "lat": est_coord[1],
                            "lon": est_coord[0],
                            "type": seg_type,
                            "label": seg.get(
                                "location", f"{seg_type.capitalize()} Stop"
                            ),
                            "radius": self.SMALL_MARKER_RADIUS,
                            "priority": 5,
                            "estimated": True,
                        }
                    )

        return markers

    def _add_waypoint_labels(
        self,
        img: Image.Image,
        markers: list[dict[str, Any]],
        static_map: "staticmap.StaticMap",
    ) -> Image.Image:
        """Add text labels near waypoints."""
        draw = ImageDraw.Draw(img)
        font = self._load_font(11)

        main_markers = [m for m in markers if m.get("priority", 0) >= 10]

        if main_markers:
            start = next((m for m in main_markers if m["type"] == "start"), None)
            if start:
                label = f"▶ Start: {start['label'][:30]}"
                draw.text((20, 220), label, fill=(34, 139, 34), font=font)

            end = next((m for m in main_markers if m["type"] == "dropoff"), None)
            if end:
                label = f"◼ End: {end['label'][:30]}"
                draw.text((20, 240), label, fill=(220, 20, 60), font=font)

            pickup = next((m for m in main_markers if m["type"] == "pickup"), None)
            if pickup:
                label = f"● Pickup: {pickup['label'][:30]}"
                draw.text((20, 260), label, fill=(30, 144, 255), font=font)

        return img

    def _add_legend(
        self,
        img: Image.Image,
        markers: list[dict[str, Any]],
        segments: list[dict[str, Any]],
    ) -> Image.Image:
        """Add a legend showing marker types and route info."""
        draw = ImageDraw.Draw(img)
        font = self._load_font(13)
        small_font = self._load_font(11)

        legend_x = img.width - 210
        legend_y = 20
        legend_width = 190

        type_counts = {}
        for marker in markers:
            t = marker["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        legend_height = 70 + len(type_counts) * 26

        shadow_offset = 3
        draw.rectangle(
            [
                (legend_x + shadow_offset, legend_y + shadow_offset),
                (
                    legend_x + legend_width + shadow_offset,
                    legend_y + legend_height + shadow_offset,
                ),
            ],
            fill=(200, 200, 200),
        )
        draw.rectangle(
            [(legend_x, legend_y), (legend_x + legend_width, legend_y + legend_height)],
            fill=(255, 255, 255),
            outline=(100, 100, 100),
            width=1,
        )

        draw.text(
            (legend_x + 10, legend_y + 10),
            "Route Legend",
            fill=(40, 40, 40),
            font=font,
        )

        draw.line(
            [
                (legend_x + 10, legend_y + 32),
                (legend_x + legend_width - 10, legend_y + 32),
            ],
            fill=(200, 200, 200),
            width=1,
        )

        y_offset = 42
        type_order = ["start", "pickup", "dropoff", "rest", "fuel", "break"]

        for marker_type in type_order:
            if marker_type not in type_counts:
                continue

            count = type_counts[marker_type]
            color = self.MARKER_COLORS.get(marker_type, {}).get("rgb", (128, 128, 128))

            cx = legend_x + 20
            cy = legend_y + y_offset + 8
            r = 8

            draw.ellipse(
                [(cx - r - 1, cy - r - 1), (cx + r + 1, cy + r + 1)],
                fill=(255, 255, 255),
                outline=(150, 150, 150),
            )
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)

            label_map = {
                "start": "Start",
                "pickup": "Pickup",
                "dropoff": "Dropoff",
                "rest": "Rest Stop",
                "fuel": "Fuel Stop",
                "break": "Break",
            }
            label = f"{label_map.get(marker_type, marker_type)}: {count}"
            draw.text(
                (legend_x + 38, legend_y + y_offset),
                label,
                fill=(60, 60, 60),
                font=small_font,
            )
            y_offset += 26

        return img

    def _add_route_info(
        self,
        img: Image.Image,
        coordinates: list[dict[str, float]],
        geometry: Optional[dict[str, Any]],
        route_data: Optional[dict[str, Any]] = None,
    ) -> Image.Image:
        """Add route information overlay with distance/duration if available."""
        draw = ImageDraw.Draw(img)
        font = self._load_font(11)

        info_x = 20
        info_y = img.height - 100

        info_lines = []

        if geometry and geometry.get("coordinates"):
            num_points = len(geometry["coordinates"])
            info_lines.append(f"Route accuracy: {num_points:,} points")
            info_lines.append("✓ Following actual roads")
        else:
            info_lines.append("⚠ Schematic view only")

        info_lines.append(f"Waypoints: {len(coordinates)}")

        if route_data:
            distance = route_data.get("total_distance") or route_data.get("distance")
            duration = route_data.get("total_duration") or route_data.get("duration")

            if distance:
                if isinstance(distance, (int, float)):
                    info_lines.append(f"Distance: {distance:.1f} miles")

            if duration:
                if isinstance(duration, (int, float)):
                    hours = int(duration)
                    minutes = int((duration - hours) * 60)
                    info_lines.append(f"Est. drive time: {hours}h {minutes}m")

        if info_lines:
            line_height = 18
            box_height = len(info_lines) * line_height + 16
            box_width = 220

            draw.rectangle(
                [
                    (info_x + 2, info_y + 2),
                    (info_x + box_width + 2, info_y + box_height + 2),
                ],
                fill=(200, 200, 200),
            )
            draw.rectangle(
                [(info_x, info_y), (info_x + box_width, info_y + box_height)],
                fill=(255, 255, 255),
                outline=(150, 150, 150),
            )

            for i, text in enumerate(info_lines):
                y_pos = info_y + 8 + i * line_height

                if text.startswith("✓"):
                    color = (34, 139, 34)
                elif text.startswith("⚠"):
                    color = (200, 150, 0)
                else:
                    color = (60, 60, 60)

                draw.text((info_x + 10, y_pos), text, fill=color, font=font)

        return img

    def _generate_fallback_map(
        self,
        coordinates: list[dict[str, float]],
        segments: list[dict[str, Any]],
        geometry: Optional[dict[str, Any]],
        width: int,
        height: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> bytes:
        """Generate a schematic map without external tile fetching."""

        def update_progress(progress: int, message: str = "") -> None:
            if progress_callback:
                try:
                    progress_callback(progress, message)
                except Exception:
                    pass

        update_progress(35, "Creating fallback map")

        img = Image.new("RGB", (width, height), color=(250, 250, 250))
        draw = ImageDraw.Draw(img)

        if not coordinates:
            return self._generate_placeholder_map(
                width, height, "No coordinates provided"
            )

        update_progress(40, "Calculating bounds")

        all_points = [(c["lon"], c["lat"]) for c in coordinates]

        if geometry and geometry.get("coordinates"):
            all_points.extend([(c[0], c[1]) for c in geometry["coordinates"]])

        if not all_points:
            return self._generate_placeholder_map(width, height, "No valid coordinates")

        lons = [p[0] for p in all_points]
        lats = [p[1] for p in all_points]

        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        lon_padding = (max_lon - min_lon) * 0.12 or 1.0
        lat_padding = (max_lat - min_lat) * 0.12 or 1.0

        min_lon -= lon_padding
        max_lon += lon_padding
        min_lat -= lat_padding
        max_lat += lat_padding

        margin = 50
        legend_width = 230
        map_width = width - legend_width - margin * 2
        map_height = height - margin * 2
        map_x = margin
        map_y = margin

        update_progress(50, "Drawing map background")

        draw.rectangle(
            [(map_x - 2, map_y - 2), (map_x + map_width + 2, map_y + map_height + 2)],
            fill=(200, 200, 200),
        )
        draw.rectangle(
            [(map_x, map_y), (map_x + map_width, map_y + map_height)],
            fill=(255, 255, 255),
        )

        self._draw_grid(
            draw,
            map_x,
            map_y,
            map_width,
            map_height,
            min_lon,
            max_lon,
            min_lat,
            max_lat,
        )

        def to_pixel(lon: float, lat: float) -> tuple[int, int]:
            x = map_x + int((lon - min_lon) / (max_lon - min_lon) * map_width)
            y = map_y + int((max_lat - lat) / (max_lat - min_lat) * map_height)
            return (x, y)

        update_progress(60, "Drawing route")

        if geometry and geometry.get("coordinates"):
            route_coords = geometry["coordinates"]
            if len(route_coords) >= 2:
                points = [to_pixel(c[0], c[1]) for c in route_coords]

                for i in range(len(points) - 1):
                    draw.line([points[i], points[i + 1]], fill=(26, 82, 118), width=5)

                for i in range(len(points) - 1):
                    draw.line([points[i], points[i + 1]], fill=(51, 136, 255), width=3)
        else:
            if len(coordinates) >= 2:
                points = [to_pixel(c["lon"], c["lat"]) for c in coordinates]
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i + 1]], fill=(180, 180, 180), width=2)

        update_progress(70, "Drawing markers")

        markers = self._extract_all_markers(coordinates, segments, geometry)
        font = self._load_font(10)

        for marker in sorted(markers, key=lambda m: m.get("priority", 0)):
            x, y = to_pixel(marker["lon"], marker["lat"])
            color = self.MARKER_COLORS.get(marker["type"], {}).get(
                "rgb", (128, 128, 128)
            )
            r = marker.get("radius", self.MARKER_RADIUS)

            draw.ellipse(
                [(x - r - 2, y - r - 2), (x + r + 2, y + r + 2)],
                fill=(255, 255, 255),
                outline=(100, 100, 100),
            )
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=color)

            if marker.get("priority", 0) >= 10:
                label = marker.get("label", "")[:20]
                if label:
                    bbox = draw.textbbox((0, 0), label, font=font)
                    text_width = bbox[2] - bbox[0]

                    label_x = x - text_width // 2
                    label_y = y + r + 4
                    draw.rectangle(
                        [
                            (label_x - 2, label_y - 1),
                            (label_x + text_width + 2, label_y + 12),
                        ],
                        fill=(255, 255, 255, 200),
                    )
                    draw.text((label_x, label_y), label, fill=(40, 40, 40), font=font)

        update_progress(80, "Adding legend")

        img = self._add_legend(img, markers, segments)

        title_font = self._load_font(16)
        draw = ImageDraw.Draw(img)
        title = "Trip Route Map"
        if not geometry or not geometry.get("coordinates"):
            title += " (Schematic)"
        draw.text((map_x + 10, map_y + 10), title, fill=(40, 40, 40), font=title_font)

        update_progress(90, "Encoding image")

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)

        update_progress(100, "Map generation complete")

        return buf.getvalue()

    def _draw_grid(
        self,
        draw: ImageDraw.ImageDraw,
        map_x: int,
        map_y: int,
        map_width: int,
        map_height: int,
        min_lon: float,
        max_lon: float,
        min_lat: float,
        max_lat: float,
    ) -> None:
        """Draw latitude/longitude grid lines."""
        grid_color = (240, 240, 240)
        text_color = (180, 180, 180)
        font = self._load_font(8)

        num_lat_lines = 5
        for i in range(num_lat_lines + 1):
            y = map_y + int(i * map_height / num_lat_lines)
            draw.line([(map_x, y), (map_x + map_width, y)], fill=grid_color, width=1)

            lat = max_lat - (i / num_lat_lines) * (max_lat - min_lat)
            draw.text((map_x + 3, y + 2), f"{lat:.2f}°", fill=text_color, font=font)

        num_lon_lines = 6
        for i in range(num_lon_lines + 1):
            x = map_x + int(i * map_width / num_lon_lines)
            draw.line([(x, map_y), (x, map_y + map_height)], fill=grid_color, width=1)

            lon = min_lon + (i / num_lon_lines) * (max_lon - min_lon)
            draw.text(
                (x + 2, map_y + map_height - 12),
                f"{lon:.2f}°",
                fill=text_color,
                font=font,
            )

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load a TrueType font with fallback."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]

        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

        return ImageFont.load_default()

    def _generate_placeholder_map(
        self,
        width: int,
        height: int,
        message: str = "Map Unavailable",
    ) -> bytes:
        """Generate a placeholder image with error message."""
        img = Image.new("RGB", (width, height), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)

        font = self._load_font(20)

        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (width - text_width) // 2
        y = (height - text_height) // 2

        draw.text((x, y), message, fill=(150, 150, 150), font=font)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()
