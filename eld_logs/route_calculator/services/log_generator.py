import io
import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from django.contrib.staticfiles import finders
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class LogGenerator:
    """
    Generate FMCSA-compliant Driver Daily Log images
    using centered duty-status lines.
    """

    template_filename = settings.TEMPLATE_FILENAME

    # -------------------------------------------------
    # GRID GEOMETRY (CALIBRATED)
    # -------------------------------------------------
    GRID_START_X = 65  # Midnight X
    GRID_START_Y = 185  # Off-duty row Y

    HOUR_WIDTH = 16.2  # px per hour
    ROW_HEIGHT = 17  # px per duty row
    TOTAL_HOURS_OFFSET = 20  # px after last midnight

    STATUS_ROW_INDEX = {
        "offDuty": 0,
        "sleeper": 1,
        "driving": 2,
        "onDuty": 3,
    }

    # -------------------------------------------------
    # REMARKS SECTION
    # -------------------------------------------------
    # X position where first remark starts (aligned with grid)
    REMARKS_START_X = 68
    # Y position for the BOTTOM of the vertical text (the baseline)
    REMARKS_BASELINE_Y = 335
    # Horizontal spacing between each remark
    REMARKS_SPACING_X = 65

    # -------------------------------------------------
    # COLORS
    # -------------------------------------------------
    COLOR_DUTY_LINE = (0, 102, 204)  # Blue
    COLOR_TEXT = (0, 0, 0)

    # -------------------------------------------------
    # GRAND TOTAL POSITION
    # -------------------------------------------------
    GRAND_TOTAL_X = 465
    GRAND_TOTAL_Y = 268

    # -------------------------------------------------
    # HEADER FIELD POSITIONS
    # -------------------------------------------------
    # Date fields
    DATE_MONTH_X = 180
    DATE_DAY_X = 225
    DATE_YEAR_X = 260
    DATE_Y = 8

    # Total miles
    TOTAL_MILES_X = 85
    TOTAL_MILES_Y = 70

    # From address
    FROM_ADDRESS_X = 90
    FROM_ADDRESS_Y = 35

    # To address
    TO_ADDRESS_X = 300
    TO_ADDRESS_Y = 35

    # Home terminal address
    HOME_TERMINAL_X = 240
    HOME_TERMINAL_Y = 90

    # Carrier name
    CARRIER_NAME_X = 240
    CARRIER_NAME_Y = 70

    # Driver name
    DRIVER_NAME_X = 240
    DRIVER_NAME_Y = 110

    # Truck/Tractor number
    TRUCK_NUMBER_X = 90
    TRUCK_NUMBER_Y = 105

    # Shipping document number
    SHIPPING_DOC_X = 30
    SHIPPING_DOC_Y = 345

    # Co-driver name
    CO_DRIVER_X = 620
    CO_DRIVER_Y = 110

    def __init__(self) -> None:
        self.fonts = self._load_fonts()

    def _get_template_path(self) -> str:
        """Get template path using Django's static file finder."""
        path = finders.find(self.template_filename)
        if not path:
            raise FileNotFoundError(
                f"Static file '{self.template_filename}' not found. "
                "Ensure it exists in one of your STATICFILES_DIRS."
            )
        return path

    # -------------------------------------------------
    # FONT LOADING
    # -------------------------------------------------
    def _load_fonts(self) -> dict[str, ImageFont.FreeTypeFont]:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]

        for font_path in paths:
            try:
                return {
                    "x-small": ImageFont.truetype(font_path, 9),
                    "small": ImageFont.truetype(font_path, 11),
                    "medium": ImageFont.truetype(font_path, 10),
                }
            except Exception:
                continue

        logger.warning("Could not load TrueType fonts, using default")
        default_font = ImageFont.load_default()
        return {"x-small": default_font, "small": default_font, "medium": default_font}

    # -------------------------------------------------
    # MAIN ENTRY POINT
    # -------------------------------------------------
    def generate_log_image(
        self,
        log_data: dict[str, Any],
        day_number: int,
        driver_name: str,
        carrier_name: str,
        main_office: str = "Washington, D.C.",
        co_driver: str = "",
        from_address: str = "",
        to_address: str = "",
        home_terminal_address: str = "",
        truck_number: str = "",
        shipping_doc: str = "",
    ) -> bytes:
        template_path = self._get_template_path()
        img = Image.open(template_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Use log_data values as fallback if parameters are empty
        total_miles = log_data.get("total_miles", "")
        from_addr = from_address or log_data.get("from_address", "")
        to_addr = to_address or log_data.get("to_address", "")
        home_terminal = home_terminal_address or log_data.get(
            "home_terminal_address", main_office
        )
        truck_num = truck_number or log_data.get("truck_number", "")
        ship_doc = shipping_doc or log_data.get("shipping_doc", "")

        self._draw_header(
            draw=draw,
            log_data=log_data,
            driver_name=driver_name,
            carrier_name=carrier_name,
            main_office=main_office,
            co_driver=co_driver,
            total_miles=total_miles,
            from_address=from_addr,
            to_address=to_addr,
            home_terminal_address=home_terminal,
            truck_number=truck_num,
            shipping_doc=ship_doc,
        )
        totals = self._draw_duty_status_lines(draw, log_data.get("events", []))
        self._draw_totals(draw, totals)
        self._draw_grand_total(draw, totals)
        self._draw_remarks(img, log_data.get("remarks", []))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    # -------------------------------------------------
    # HEADER
    # -------------------------------------------------
    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        log_data: dict[str, Any],
        driver_name: str,
        carrier_name: str,
        main_office: str,
        co_driver: str,
        total_miles: Any,
        from_address: str,
        to_address: str,
        home_terminal_address: str,
        truck_number: str,
        shipping_doc: str,
    ) -> None:
        # Date
        date = log_data.get("date", datetime.now().strftime("%m/%d/%Y"))
        month, day, year = date.split("/")

        draw.text(
            (self.DATE_MONTH_X, self.DATE_Y),
            month,
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )
        draw.text(
            (self.DATE_DAY_X, self.DATE_Y),
            day,
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )
        draw.text(
            (self.DATE_YEAR_X, self.DATE_Y),
            year,
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

        # Total miles
        draw.text(
            (self.TOTAL_MILES_X, self.TOTAL_MILES_Y),
            str(total_miles),
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

        # From address
        draw.text(
            (self.FROM_ADDRESS_X, self.FROM_ADDRESS_Y),
            str(from_address),
            font=self.fonts["medium"],
            fill=self.COLOR_TEXT,
        )

        # To address
        draw.text(
            (self.TO_ADDRESS_X, self.TO_ADDRESS_Y),
            str(to_address),
            font=self.fonts["medium"],
            fill=self.COLOR_TEXT,
        )

        # Carrier name
        draw.text(
            (self.CARRIER_NAME_X, self.CARRIER_NAME_Y),
            carrier_name,
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

        # Home terminal address
        draw.text(
            (self.HOME_TERMINAL_X, self.HOME_TERMINAL_Y),
            str(home_terminal_address),
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

        # Driver name
        draw.text(
            (self.DRIVER_NAME_X, self.DRIVER_NAME_Y),
            driver_name,
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

        # Truck/Tractor number
        draw.text(
            (self.TRUCK_NUMBER_X, self.TRUCK_NUMBER_Y),
            str(truck_number),
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

        # Shipping document number
        draw.text(
            (self.SHIPPING_DOC_X, self.SHIPPING_DOC_Y),
            str(shipping_doc),
            font=self.fonts["x-small"],
            fill=self.COLOR_TEXT,
        )

        # Co-driver name
        if co_driver:
            draw.text(
                (self.CO_DRIVER_X, self.CO_DRIVER_Y),
                co_driver,
                font=self.fonts["small"],
                fill=self.COLOR_TEXT,
            )

    # -------------------------------------------------
    # DUTY STATUS LINES
    # -------------------------------------------------
    def _draw_duty_status_lines(
        self,
        draw: ImageDraw.ImageDraw,
        events: list[dict[str, Any]],
    ) -> dict[str, float]:
        totals = {k: 0.0 for k in self.STATUS_ROW_INDEX}
        prev_row_center_y = None

        for event in sorted(events, key=lambda e: float(e["start"])):
            status = event.get("status")
            if status not in self.STATUS_ROW_INDEX:
                continue

            start = max(0.0, float(event["start"]))
            end = min(24.0, float(event["end"]))
            duration = end - start

            row_index = self.STATUS_ROW_INDEX[status]
            row_top_y = self.GRID_START_Y + (row_index * self.ROW_HEIGHT)
            row_center_y = row_top_y + (self.ROW_HEIGHT // 2)

            x1 = int(self.GRID_START_X + (start * self.HOUR_WIDTH))
            x2 = int(self.GRID_START_X + (end * self.HOUR_WIDTH))

            if prev_row_center_y is not None and prev_row_center_y != row_center_y:
                draw.line(
                    [(x1, prev_row_center_y), (x1, row_center_y)],
                    fill=self.COLOR_DUTY_LINE,
                    width=2,
                )

            draw.line(
                [(x1, row_center_y), (x2, row_center_y)],
                fill=self.COLOR_DUTY_LINE,
                width=2,
            )

            totals[status] += duration
            prev_row_center_y = row_center_y

        return totals

    # -------------------------------------------------
    # TOTAL HOURS PER STATUS
    # -------------------------------------------------
    def _draw_totals(
        self,
        draw: ImageDraw.ImageDraw,
        totals: dict[str, float],
    ) -> None:
        total_x = int(
            self.GRID_START_X + (24 * self.HOUR_WIDTH) + self.TOTAL_HOURS_OFFSET
        )

        for status, hours in totals.items():
            row_index = self.STATUS_ROW_INDEX[status]
            row_top_y = self.GRID_START_Y + (row_index * self.ROW_HEIGHT)
            row_center_y = row_top_y + (self.ROW_HEIGHT // 2)

            draw.text(
                (total_x, row_center_y - 6),
                f"{hours:.2f}",
                font=self.fonts["small"],
                fill=self.COLOR_TEXT,
            )

    # -------------------------------------------------
    # GRAND TOTAL (ALL STATUSES)
    # -------------------------------------------------
    def _draw_grand_total(
        self,
        draw: ImageDraw.ImageDraw,
        totals: dict[str, float],
    ) -> None:
        grand_total = sum(totals.values())

        draw.text(
            (self.GRAND_TOTAL_X, self.GRAND_TOTAL_Y),
            f"={grand_total:.2f}",
            font=self.fonts["small"],
            fill=self.COLOR_TEXT,
        )

    # -------------------------------------------------
    # REMARKS (VERTICAL TEXT, 90 DEGREES)
    # -------------------------------------------------
    # TODO: Fix remarks x positioning
    def _draw_remarks(
        self,
        img: Image.Image,
        remarks: list[dict[str, str]],
    ) -> None:
        x = self.REMARKS_START_X

        for remark in remarks:
            location = remark.get("location")
            if not location:
                continue

            self._draw_vertical_text(
                img=img,
                x=x,
                baseline_y=self.REMARKS_BASELINE_Y,
                text=location,
            )

            x += self.REMARKS_SPACING_X

    def _draw_vertical_text(
        self,
        img: Image.Image,
        x: int,
        baseline_y: int,
        text: str,
    ) -> None:
        """
        Draw text rotated 90 degrees counterclockwise.
        The text will read from bottom to top.

        Args:
            img: The image to draw on
            x: X position for the left edge of the rotated text
            baseline_y: Y position for the bottom of the rotated text
            text: The text to draw
        """
        font = self.fonts["x-small"]

        # Create a temporary image to measure and draw the text
        dummy = ImageDraw.Draw(img)
        bbox = dummy.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Add padding
        pad = 2
        txt_img = Image.new(
            "RGBA",
            (text_w + pad * 2, text_h + pad * 2),
            (255, 255, 255, 0),
        )

        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text(
            (pad, pad),
            text,
            font=font,
            fill=self.COLOR_TEXT,
        )

        # Rotate 90 degrees counterclockwise
        # After rotation: original width becomes height, original height becomes width
        rotated = txt_img.rotate(90, expand=True)

        # Calculate paste position
        # After 90° CCW rotation:
        # - rotated.width = original height (text_h + pad*2)
        # - rotated.height = original width (text_w + pad*2)
        #
        # We want:
        # - Left edge of rotated text at x
        # - Bottom edge of rotated text at baseline_y
        paste_x = x
        paste_y = baseline_y - rotated.height

        img.paste(rotated, (paste_x, paste_y), rotated)

    def _draw_rotated_text(
        self,
        img: Image.Image,
        x: int,
        y: int,
        text: str,
        angle: float,
    ) -> None:
        """
        Draw text at an arbitrary angle.
        For 90-degree rotation, use _draw_vertical_text instead for better positioning.

        Args:
            img: The image to draw on
            x: X position (interpretation depends on angle)
            y: Y position (interpretation depends on angle)
            text: The text to draw
            angle: Rotation angle in degrees (counterclockwise)
        """
        font = self.fonts["small"]

        # Measure text
        dummy = ImageDraw.Draw(img)
        bbox = dummy.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        pad = 4
        txt_img = Image.new(
            "RGBA",
            (text_w + pad * 2, text_h + pad * 2),
            (255, 255, 255, 0),
        )

        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text(
            (pad, pad),
            text,
            font=font,
            fill=self.COLOR_TEXT,
        )

        # Rotate
        rotated = txt_img.rotate(angle, expand=True)

        # Position based on angle
        if angle == 90:
            # Text reads bottom to top
            # Bottom-left of rotated image at (x, y)
            paste_x = x
            paste_y = y - rotated.height
        elif angle == -90 or angle == 270:
            # Text reads top to bottom
            # Top-left of rotated image at (x, y)
            paste_x = x
            paste_y = y
        elif angle == 45:
            # Diagonal text - center around the point
            paste_x = x - rotated.width // 2
            paste_y = y - rotated.height // 2
        else:
            # Default: center the rotated text around (x, y)
            orig_cx = txt_img.width // 2
            orig_cy = txt_img.height // 2
            rot_cx = rotated.width // 2
            rot_cy = rotated.height // 2
            paste_x = int(x + orig_cx - rot_cx)
            paste_y = int(y + orig_cy - rot_cy)

        img.paste(rotated, (paste_x, paste_y), rotated)
