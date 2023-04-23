import json
import os

import boto3

os.environ['AWS_DEFAULT_REGION'] = "eu-west-1"

dynamodb_res = boto3.resource("dynamodb")
table = dynamodb_res.Table("IppDejPdfDataTable")

datas = json.load(open("scripts/datas.json", "r"))

with table.batch_writer() as writer:
    for item in datas:
        writer.put_item(Item=item)

print("items added in dynamodb")
