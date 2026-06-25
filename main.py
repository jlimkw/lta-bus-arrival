from datetime import datetime
from enum import StrEnum
from multiprocessing import process
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lta_api_key: str = Field(default="")

    model_config = ConfigDict(env_file=".env")


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
    origin_code: str = Field(max_length=5, alias="OriginCode")
    destination_code: str = Field(max_length=5, alias="DestinationCode")
    estimated_arrival: datetime = Field(alias="EstimatedArrival")
    monitored: Literal[0, 1] = Field(alias="Monitored")
    latitude: float = Field(alias="Latitude")
    longitude: float = Field(alias="Longitude")
    visit_num: int = Field(alias="VisitNumber")
    load: BusLoad = Field(alias="Load")
    feature: str = Field(alias="Feature")
    type: BusType = Field(alias="Type")


class BusArrival(BaseModel):
    service_num: str = Field(max_length=4, alias="ServiceNo")
    operator: str = Field(max_length=4, alias="Operator")
    next_bus: BusArrivalDetails = Field(alias="NextBus")
    next_bus2: BusArrivalDetails | None = Field(alias="NextBus2")
    next_bus3: BusArrivalDetails | None = Field(alias="NextBus3")


def get_bus_arrivals(bus_stop_code: str) -> dict:
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
    return [BusArrival.model_validate(service) for service in arrivals["Services"]]


def main():
    print(f"Bus stop {SEASONS_PARK_BUS_STOP} outside Seasons Park")
    arrivals = get_bus_arrivals(SEASONS_PARK_BUS_STOP)
    processed_arrivals = process_bus_arrivals(arrivals)
    print(processed_arrivals)

    print(f"Bus stop {SEASONS_PARK_BUS_STOP_OPPOSITE} opposite Seasons Park")
    arrivals_opposite = get_bus_arrivals(SEASONS_PARK_BUS_STOP_OPPOSITE)


if __name__ == "__main__":
    main()
