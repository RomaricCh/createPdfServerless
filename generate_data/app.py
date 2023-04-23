import dataclasses
import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import List

import boto3
import simplejson
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent

TABLE_NAME_EXPORT = os.environ.get("TABLE_NAME_EXPORT")
TABLE_NAME_DATA = os.environ.get("TABLE_NAME_DATA")
URL_SQS_QUEUE = os.environ.get("URL_SQS_QUEUE")

logger = Logger()
tracer = Tracer()
metrics = Metrics()
app = ApiGatewayResolver()


@dataclass
class RequestPdf:
    sport: str
    sportsman: str
    uuid: str


@dataclass
class RequestExportDto:
    uuid: str
    create_date: str
    nb_pdf_exported: int = 0
    nb_total_pdf: int = 0


@dataclass
class StatsRider:
    season: Decimal
    category: str
    bike: str
    starts: Decimal
    poles: Decimal
    first_position: Decimal
    second_position: Decimal
    third_position: Decimal
    podiums: Decimal
    points: Decimal
    position: Decimal


@dataclass
class RiderDto:
    sportsman: str
    stats: List[StatsRider]
    total_first_pos: int = 0
    total_first_pos_motogp: int = 0
    total_first_pos_moto2: int = 0
    total_first_pos_moto3: int = 0

    total_second_pos: int = 0
    total_second_pos_motogp: int = 0
    total_second_pos_moto2: int = 0
    total_second_pos_moto3: int = 0

    total_third_pos: int = 0
    total_third_pos_motogp: int = 0
    total_third_pos_moto2: int = 0
    total_third_pos_moto3: int = 0

    def append_stat(self, stat: StatsRider) -> None:
        self.total_first_pos += stat.first_position
        self.increment_first_pos(int(stat.first_position), stat.category)
        self.total_second_pos += stat.second_position
        self.increment_second_pos(int(stat.second_position), stat.category)
        self.total_third_pos += stat.third_position
        self.increment_third_pos(int(stat.third_position), stat.category)
        self.stats.append(stat)

    def increment_first_pos(self, value: int, categorie: str):
        if categorie == "MotoGP":
            self.total_first_pos_motogp += value
        if categorie == "Moto2":
            self.total_first_pos_moto2 += value
        if categorie in ["Moto3", "125cc"]:
            self.total_first_pos_moto3 += value

    def increment_second_pos(self, value: int, categorie: str):
        if categorie == "MotoGP":
            self.total_second_pos_motogp += value
        if categorie == "Moto2":
            self.total_second_pos_moto2 += value
        if categorie in ["Moto3", "125cc"]:
            self.total_second_pos_moto3 += value

    def increment_third_pos(self, value: int, categorie: str):
        if categorie == "MotoGP":
            self.total_third_pos_motogp += value
        if categorie == "Moto2":
            self.total_third_pos_moto2 += value
        if categorie in ["Moto3", "125cc"]:
            self.total_third_pos_moto3 += value


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context):
    try:
        for record in event.records:
            request_info = RequestPdf(**json.loads(record.body))

            logger.info(f"Generate data for {request_info.uuid}")
            table_data = boto3.resource("dynamodb").Table(TABLE_NAME_DATA)

            data = table_data.get_item(Key={"sport": request_info.sport, "sportsman": request_info.sportsman})["Item"]
            rider: RiderDto = RiderDto(sportsman=data["sportsman"], stats=[])
            for stat in data["stats"]:
                stat_rider = StatsRider(**stat)
                rider.append_stat(stat_rider)

            sqs = boto3.client("sqs")
            msgSqs = {
                "pk": request_info.uuid,
                "data": dataclasses.asdict(rider)
            }
            sqs.send_message(QueueUrl=URL_SQS_QUEUE,
                             MessageBody=simplejson.dumps(msgSqs))

    except Exception as e:
        logger.exception(e)
        raise e
