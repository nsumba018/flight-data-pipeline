import boto3


BUCKET_NAME = (
    "flight-data-pipeline-nsumba-551656632261-us-east-1-an"
)

S3_PREFIX = "incoming"


s3 = boto3.client("s3")


def upload_attachment_to_s3(
    attachment_bytes,
    uid,
    original_filename
):
    """
    Upload an email attachment directly to S3
    without saving it to local disk.
    """

    uid_number = uid.decode()

    s3_filename = (
        f"X2-FS_uid_{uid_number}.txt"
    )

    s3_key = (
        f"{S3_PREFIX}/{s3_filename}"
    )

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=attachment_bytes
    )

    print(
        f"Uploaded UID {uid_number} "
        f"to s3://{BUCKET_NAME}/{s3_key}"
    )