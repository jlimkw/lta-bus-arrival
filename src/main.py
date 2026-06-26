from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

import flet as ft
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings
from rich import print


class Settings(BaseSettings):
    lta_api_key: str = Field(default="")

    model_config = ConfigDict(env_file=str(Path(__file__).resolve().parent / ".env"))


settings = Settings()

LTA_BUS_ARRIVALS_URL = "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival"
SEASONS_PARK_BUS_STOP = "55029"
SEASONS_PARK_BUS_STOP_OPPOSITE = "55021"


class BusLoad(StrEnum):
    SEA = "SEA"  # Seats Available
    SDA = "SDA"  # Standing Available
    LSD = "LSD"  # Limited Standing


class BusType(StrEnum):
    SD = "SD"  # Single Deck
    DD = "DD"  # Double Deck
    BD = "BD"  # Bendy


class BusArrivalDetails(BaseModel):
    origin_code: str | None = Field(max_length=5, alias="OriginCode")
    destination_code: str | None = Field(max_length=5, alias="DestinationCode")
    estimated_arrival: datetime | None = Field(alias="EstimatedArrival")
    monitored: Literal[0, 1] = Field(alias="Monitored")
    latitude: float | None = Field(alias="Latitude")
    longitude: float | None = Field(alias="Longitude")
    visit_num: int | None = Field(alias="VisitNumber")
    load: BusLoad | None = Field(alias="Load")
    feature: str | None = Field(alias="Feature")
    type: BusType | None = Field(alias="Type")

    @field_validator("*", mode="before")
    def empty_str_to_none(cls, value):
        return None if value == "" else value


class BusArrival(BaseModel):
    service_num: str = Field(max_length=4, alias="ServiceNo")
    operator: str = Field(max_length=4, alias="Operator")
    next_bus: BusArrivalDetails = Field(alias="NextBus")
    next_bus2: BusArrivalDetails = Field(alias="NextBus2")
    next_bus3: BusArrivalDetails = Field(alias="NextBus3")


def get_bus_arrivals_api(bus_stop_code: str) -> dict:
    if not settings.lta_api_key:
        print("LTA API key not set")
    with httpx.Client() as client:
        response = client.get(
            LTA_BUS_ARRIVALS_URL,
            headers={"AccountKey": settings.lta_api_key, "Accept": "application/json"},
            params={"BusStopCode": bus_stop_code},
        )
        response.raise_for_status()
        return response.json()


def process_bus_arrivals(arrivals: dict) -> list[BusArrival]:
    if not arrivals.get("Services"):
        return []
    validated_arrivals = []
    for service in arrivals["Services"]:
        try:
            validated_arrivals.append(BusArrival.model_validate(service))
        except ValidationError:
            print(f"LTA data issue for {service['ServiceNo']}")
    return validated_arrivals


def get_next_bus_info(bus: BusArrivalDetails) -> str:
    est_arrival = (
        str(bus.estimated_arrival).split(" ")[1].split("+")[0]
        if bus.estimated_arrival
        else "no data"
    )
    match bus.load:
        case BusLoad.SEA:
            load = "Seats Available"
        case BusLoad.SDA:
            load = "Standing Available"
        case BusLoad.LSD:
            load = "Limited Standing"
        case _:
            load = "no data"
    match bus.type:
        case BusType.SD:
            type = "Single Deck"
        case BusType.DD:
            type = "Double Deck"
        case BusType.BD:
            type = "Bendy"
        case _:
            type = "no data"
    return f"{est_arrival} ({load}) ({type})"


def main():
    print(f"Bus stop {SEASONS_PARK_BUS_STOP} outside Seasons Park")
    arrivals = get_bus_arrivals_api(SEASONS_PARK_BUS_STOP)
    for bus in process_bus_arrivals(arrivals):
        print(
            f"Bus: {bus.service_num} ({'SBSTransit' if bus.operator == 'SBST' else 'Tower Transit'})"
        )
        print(
            f"Estimated arrivals: {get_next_bus_info(bus.next_bus)}, {get_next_bus_info(bus.next_bus2)}, {get_next_bus_info(bus.next_bus3)}"
        )

    print(f"Bus stop {SEASONS_PARK_BUS_STOP_OPPOSITE} opposite Seasons Park")
    arrivals_opposite = get_bus_arrivals_api(SEASONS_PARK_BUS_STOP_OPPOSITE)
    for bus in process_bus_arrivals(arrivals_opposite):
        print(f"Bus: {bus.service_num} ({bus.operator})")
        print(
            f"Estimated arrivals: {get_next_bus_info(bus.next_bus)}, {get_next_bus_info(bus.next_bus2)}, {get_next_bus_info(bus.next_bus3)}"
        )


def flet_main(page: ft.Page):
    page.title = "Bus Arrivals"
    page.padding = 0
    page.spacing = 0
    page.window.height = 800
    page.window.width = 500
    buses = BusArrivalsFlet()
    page.add(buses)


@ft.control
class BusArrivalsFlet(ft.Container):
    def init(self):
        self.bus_stop_input = ft.TextField(
            label="Bus Stop number",
            hint_text=SEASONS_PARK_BUS_STOP,
            width=300,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            bgcolor=ft.Colors.GREEN,
            autofocus=True,
            max_length=5,
            # 1. The Gatekeeper: Blocks non-numeric keyboard input instantly
            input_filter=ft.InputFilter(
                allow=True, regex_string=r"[0-9]", replacement_string=""
            ),
            # 2. Mobile Friendly: Opens the numeric keypad layout on iOS and Android
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.paragraph_display = ft.Text(width=400)
        self.width = 500
        self.height = 800
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = ft.BorderRadius.all(20)
        self.padding = 20
        self.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                # Row 1: The Bus Stop Input Field
                ft.Row(
                    controls=[self.bus_stop_input],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.FilledButton("Search", on_click=self.handle_search),
                        ft.OutlinedButton("Clear", on_click=self.handle_clear),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,  # Adds 10px of horizontal spacing between the buttons
                ),
                ft.Row(
                    controls=[
                        self.paragraph_display,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,  # Aligns rows starting from the top
            spacing=15,  # Adds 15px of vertical spacing between each Row block
        )

    def handle_search(self, e):
        bus_stop = self.bus_stop_input.value
        if bus_stop:
            arrivals = get_bus_arrivals_api(bus_stop)
            processed_arrivals = process_bus_arrivals(arrivals)
            text_spans = []
            if not processed_arrivals:
                text_spans.append(
                    ft.TextSpan(
                        "No active bus service data found for this stop.",
                        style=ft.TextStyle(color=ft.Colors.RED_400),
                    )
                )
            else:
                for bus in processed_arrivals:
                    operator_name = (
                        "SBSTransit" if bus.operator == "SBST" else "Tower Transit"
                    )
                    # 1. BOLD line for the Bus Number and Operator
                    text_spans.append(
                        ft.TextSpan(
                            text=f"Bus: {bus.service_num} ({operator_name})\n",
                            style=ft.TextStyle(
                                weight=ft.FontWeight.BOLD,
                                size=16,
                                color=ft.Colors.BLUE_400,
                            ),
                        )
                    )
                    # 2. NORMAL label for arrivals header
                    text_spans.append(
                        ft.TextSpan(
                            text="Estimated arrivals:\n",
                            style=ft.TextStyle(color=ft.Colors.GREEN),
                        )
                    )
                    # 3. INDIVIDUAL lines for each ETA time block
                    text_spans.append(
                        ft.TextSpan(text=f"  • {get_next_bus_info(bus.next_bus)}\n")
                    )
                    text_spans.append(
                        ft.TextSpan(text=f"  • {get_next_bus_info(bus.next_bus2)}\n")
                    )
                    text_spans.append(
                        ft.TextSpan(text=f"  • {get_next_bus_info(bus.next_bus3)}\n\n")
                    )
                    # Inject the styled blocks into the display object
                self.paragraph_display.spans = text_spans
        else:
            self.paragraph_display.spans = [
                ft.TextSpan(
                    f"Please enter a bus stop code first. (eg. {SEASONS_PARK_BUS_STOP_OPPOSITE})"
                )
            ]
        self.update()

    def handle_clear(self, e):
        self.bus_stop_input.value = ""
        self.paragraph_display.spans = []
        self.paragraph_display.value = ""
        self.update()


if __name__ == "__main__":
    # main()
    ft.run(flet_main)
