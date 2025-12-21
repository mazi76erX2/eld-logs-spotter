from route_calculator.services.log_generator import LogGenerator

log_data = {
    "date": "04/09/2021",
    "total_miles": 350,
    "from_address": "Richmond, VA",
    "to_address": "Newark, NJ",
    "home_terminal_address": "Washington, D.C.",
    "truck_number": "123, 20544",
    "shipping_doc": "101601",
    "events": [
        {"start": 0, "end": 6, "status": "offDuty"},
        {"start": 6, "end": 7.5, "status": "onDuty"},
        {"start": 7.5, "end": 9, "status": "driving"},
        {"start": 9, "end": 9.5, "status": "onDuty"},
        {"start": 9.5, "end": 12, "status": "driving"},
        {"start": 12, "end": 13, "status": "offDuty"},
        {"start": 13, "end": 15, "status": "driving"},
        {"start": 15, "end": 15.5, "status": "onDuty"},
        {"start": 15.5, "end": 16, "status": "driving"},
        {"start": 16, "end": 17.75, "status": "sleeper"},
        {"start": 17.75, "end": 19, "status": "driving"},
        {"start": 19, "end": 21, "status": "onDuty"},
        {"start": 21, "end": 24, "status": "offDuty"},
    ],
    "remarks": [
        {"location": "Richmond, VA"},
        {"location": "Fredericksburg, VA"},
        {"location": "Baltimore, MD"},
        {"location": "Philadelphia, PA"},
        {"location": "Cherry Hill, NJ"},
        {"location": "Newark, NJ"},
    ],
}

gen = LogGenerator()
img = gen.generate_log_image(
    log_data,
    1,
    "John E. Doe",
    "John Doe's Transportation",
    "Washington, D.C.",
    "Jane Doe",  # Co-driver
)

with open("output_daily_log.png", "wb") as f:
    f.write(img)

print("Generated output_daily_log.png")
