import boto3

BUCKET_NAME = "ippdejpdf-export"

s3 = boto3.client("s3")
continue_retieve_object = True

key_objects_s3 = []
continuation_token = None
while continue_retieve_object:
    param_s3 = {
        "Bucket": BUCKET_NAME
    }
    if continuation_token:
        param_s3['continuation_token'] = continuation_token

    result_s3 = s3.list_objects_v2(**param_s3)

    if not result_s3['IsTruncated']:
        continue_retieve_object = False
    else:
        continuation_token = result_s3['NextContinuationToken']

    if 'Contents' not in result_s3:
        break
    for item in result_s3['Contents']:
        key_objects_s3.append(item['Key'])

for key in key_objects_s3:
    s3.delete_object(Bucket=BUCKET_NAME, Key=key)

print(f"{len(key_objects_s3)} object(s) deleted")
