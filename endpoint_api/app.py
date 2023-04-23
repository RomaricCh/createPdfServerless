import json
import os
import pickle
import uuid
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import content_types
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver, Response
from aws_lambda_powertools.logging import correlation_paths
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_sqs import SQSClient

TABLE_NAME_DATA = os.environ.get("TABLE_NAME_DATA")
URL_SQS_QUEUE = os.environ.get("URL_SQS_QUEUE")
BUCKET_NAME = os.environ.get("BUCKET_NAME")

logger = Logger()
tracer = Tracer()
metrics = Metrics()
app = ApiGatewayResolver()


@dataclass
class RequestPdf:
    sport: str
    sportsman: str
    uuid: Optional[str] = None

    def __post_init__(self):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())


@app.exception_handler(ValueError)
def handle_value_error(ex: ValueError):
    metadata = {"path": app.current_event.path}
    logger.error(f"Error on request: {ex}", extra=metadata)

    return Response(
        status_code=400,
        content_type=content_types.TEXT_PLAIN,
        body=json.dumps({"error": str(ex)}),
    )


@app.post("/request-pdf/<sport>/<sportsman>")
@tracer.capture_method
def request_pdf(sport: str, sportsman: str) -> dict:
    sportsman = unquote(sportsman)
    sport = unquote(sport)
    dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
    table_data = dynamodb.Table(TABLE_NAME_DATA)

    result_data = table_data.query(KeyConditionExpression=Key("sport").eq(sport) & Key("sportsman").eq(sportsman))
    if result_data['Count'] == 0:
        raise ValueError(f"no data found for sport {sport} and sportsman {sportsman}")

    if sport != "motorbike":
        raise ValueError(f"not yet implemented for {sport}")

    request_pdf_info = RequestPdf(sport, sportsman)

    sqs: SQSClient = boto3.client("sqs")
    sqs.send_message(QueueUrl=URL_SQS_QUEUE, MessageBody=json.dumps(request_pdf_info.__dict__))

    return {"uuid": request_pdf_info.uuid}


@app.get("/pdf/<uuid>")
@tracer.capture_method()
def get_presigned_url_pdf(uuid: str) -> dict:
    s3_cient = boto3.client("s3")
    key = f"{uuid}.pdf"
    try:
        s3_cient.get_object(Bucket=BUCKET_NAME, Key=key)

        result = s3_cient.generate_presigned_url(ClientMethod="get_object",
                                                 Params={"Bucket": BUCKET_NAME, "Key": key},
                                                 ExpiresIn=60)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.error(f"file ${key} not found in bucket ${BUCKET_NAME}")
            raise ValueError("No file found. Try later")
        else:
            logger.exception(e)
            raise e

    return {"response": result}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True
)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.exception(e)
        raise
