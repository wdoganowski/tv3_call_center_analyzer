import boto3
import os
import uuid
import logging

# Initiate the logging module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(event, context):
    # Retrieve the S3 bucket and object information from the event
    try:
        input_s3_bucket = event['Records'][0]['s3']['bucket']['name']
        input_s3_key = event['Records'][0]['s3']['object']['key']
    except KeyError:
        logger.error(f"Invalid event data {event}")
        return {
            'statusCode': 400,
            'body': 'Invalid event data'
        }
    
    # Verify if it is an mp3 file
    if not input_s3_key.endswith('.mp3'):
        logger.error(f"Invalid file type: s3://{input_s3_bucket}/{input_s3_key}")
        return {
            'statusCode': 400,
            'body': 'Invalid file type'
        }
    logger.info(f"Processing file: s3://{input_s3_bucket}/{input_s3_key}")
    
    # Retrieve the output S3 bucket from the environment variables
    try:
        output_s3_bucket = os.environ['TRANSCRIBEBUCKET_BUCKET_NAME']
    except KeyError:
        logger.error("Environment variable OUTPUT_BUCKET not set")
        return {
            'statusCode': 500,
            'body': 'Internal server error: Environment variable TRANSCRIBEBUCKET_BUCKET_NAME not set'
        }
    
    # Generate a unique job name and output file name
    job_name = str(uuid.uuid4())
    output_s3_key = input_s3_key.replace('.mp3', '.txt')
    logger.info(f"Job name: {job_name}")
    logger.info(f"Output file name: s3://{output_s3_bucket}/{output_s3_key}")
    
    # Create an Amazon Transcribe client
    try:
        transcribe_client = boto3.client('transcribe')
    except Exception as e:
        logger.error(f"Error creating Amazon Transcribe client: {e}")
        return {
            'statusCode': 500,
            'body': 'Internal server error: Error creating Amazon Transcribe client'
        }
    
    # Set the S3 URI for the input audio file
    s3_uri = f"s3://{input_s3_bucket}/{input_s3_key}"
    
    # Start the transcription job
    try:
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode='auto',  # Auto detect the language
            LanguageOptions=['en-US', 'lt-LT', 'lv-LV', 'et-EE', 'ru-RU'],  # Specify the languages you expect to be present
            MediaFormat='mp3',
            Media={
                'MediaFileUri': s3_uri
            },
            OutputBucketName=output_s3_bucket,
            OutputKey=output_s3_key
        )
    except Exception as e:
        logger.error(f"Error starting transcription job: {e}")
        return {
            'statusCode': 500,
            'body': 'Internal server error: Error starting transcription job'
        }
    
    logger.info(f"Transcription job started with name: {job_name}")
    
    return {
        'statusCode': 200,
        'body': response
    }