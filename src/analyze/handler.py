import boto3
from botocore.config import Config
import os
import uuid
import logging
import json
import time

import instructions

# Initiate the logging module
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define the directories
TRANSCRIBE_DIR = 'recordings/'
TRANSCRIBE_EXT = '.mp3'
ANALYZE_DIR = 'transcripts/'
ANALYZE_EXT = '.json'
OUTPUT_DIR = 'output/'
OUTPUT_EXT = '.txt'

handled_event_names = ['ObjectCreated:Copy', 'ObjectCreated:Put']


def transcribe(input_s3_bucket: str, input_s3_key: str) -> dict:
    # Verify if it is an mp3 file
    if not input_s3_key.endswith(TRANSCRIBE_EXT):
        logger.warning(
            f"Invalid file type: s3://{input_s3_bucket}/{input_s3_key}")
        return {
            'statusCode': 400,
            'body': 'Invalid file type'
        }
    logger.info(f"Transcribing file: s3://{input_s3_bucket}/{input_s3_key}")

    # Generate a unique job name and output file name
    job_name = str(uuid.uuid4())
    output_s3_bucket = input_s3_bucket  # Use the same S3 bucket for output
    output_s3_key = input_s3_key.replace(
        TRANSCRIBE_DIR, ANALYZE_DIR, 1).replace(TRANSCRIBE_EXT, ANALYZE_EXT)
    logger.info(f"Job name: {job_name}")
    logger.info(f"Output file name: s3://{output_s3_bucket}/{output_s3_key}")

    # Create an Amazon Transcribe client
    try:
        transcribe_client = boto3.client('transcribe')
    except Exception as e:
        logger.error(f"Error creating Amazon Transcribe client: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error creating Amazon Transcribe client: {e}'
        }

    # Set the S3 URI for the input audio file
    s3_uri = f"s3://{input_s3_bucket}/{input_s3_key}"

    # Start the transcription job
    try:
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            IdentifyLanguage=True,  # Auto detect the language
            # Specify the languages you expect to be present
            LanguageOptions=['en-US', 'lt-LT', 'lv-LV', 'et-ET', 'ru-RU'],
            MediaFormat='mp3',
            Media={
                'MediaFileUri': s3_uri
            },
            OutputBucketName=output_s3_bucket,
            OutputKey=output_s3_key,
            Settings={
                'ShowSpeakerLabels': True,  # Enable speaker identification
                'MaxSpeakerLabels': 4,  # Specify the maximum number of speakers to identify
                'ShowAlternatives': True,  # Enable alternative transcriptions
                'MaxAlternatives': 2  # Generate 2 alternative transcriptions
            }
        )
    except Exception as e:
        logger.error(f"Error starting transcription job: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error starting transcription job: {e}'
        }

    logger.info(f"Transcription job started with name: {job_name}")
    logger.debug(response)

    return {
        'statusCode': 200,
        'body': 'OK'
    }


def format_content(data: dict) -> str:
    # Source: https://github.com/aws-samples/amazon-bedrock-samples/blob/main/generative-ai-solutions/recordings-summary-generator/recordings-summary-generation.yaml
    lines = []
    line = ''
    speaker = 'spk_1'
    most_recent_speaker = 'spk_1'
    # Loop through the speakers and add them to the transcription.
    try:
        items = data['results']['items']
        
        for item in items:
            if item.get('start_time'):  # This is a spoken item
                speaker = item['speaker_label']

                if speaker == most_recent_speaker:
                    # Append the content to line and repeat
                    line+=f" {item['alternatives'][0]['content']}"

                else:
                    # New speaker
                    lines.append(f'{line}\n\n')
                    most_recent_speaker = speaker
                    line=f"{item['start_time']}\t{speaker}\t{item['alternatives'][0]['content']}"

            elif item['type'] == 'punctuation':
                line+=item['alternatives'][0]['content']

        lines.append(line)
            
    except Exception as e:
        logger.error(f"Error parsing result items: {e}")
        return ""

    speaker_formatted_content = ''
    for line in lines:
        speaker_formatted_content+=line
        
    return speaker_formatted_content


def analyze(input_s3_bucket: str, input_s3_key: str) -> dict:
    # Verify if it is an json file
    if not input_s3_key.endswith(ANALYZE_EXT):
        logger.warning(
            f"Invalid file type: s3://{input_s3_bucket}/{input_s3_key}")
        return {
            'statusCode': 400,
            'body': 'Invalid file type'
        }
    logger.info(f"Analyzing file: s3://{input_s3_bucket}/{input_s3_key}")

    # Generate a unique job name and output file name
    output_s3_bucket = input_s3_bucket  # Use the same S3 bucket for output
    output_s3_key = input_s3_key.replace(
        ANALYZE_DIR, OUTPUT_DIR, 1).replace(ANALYZE_EXT, OUTPUT_EXT)
    logger.info(f"Output file name: s3://{output_s3_bucket}/{output_s3_key}")

    # Read the input json file from s3
    try:
        s3 = boto3.resource('s3')
    except Exception as e:
        logger.error(f"Error creating Amazon S3 client: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error creating Amazon S3 client: {e}'
        }
    try:
        obj = s3.Object(input_s3_bucket, input_s3_key)
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error reading input file: {e}'
        }
    try:
        json_data = obj.get()['Body'].read().decode('utf-8')
        json_data = json.loads(json_data)
    except Exception as e:
        logger.error(f"Error decoding input file: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error decoding input file: {e}'
        }
            
    # Get the transcript from the Amazon Transcribe job
    try:
        language_code = json_data['results']['language_code']
    except KeyError:
        logger.error("Error getting language code")
        return {
            'statusCode': 500,
            'body': 'Internal server error: Error getting language code'
        }
    logger.info(f"Input data is in language {language_code}")
    # try:
    #     speaker_labels = json_data['results']['speaker_labels']
    # except KeyError:
    #     logger.error("Error getting speaker labels")
    #     return {
    #         'statusCode': 500,
    #         'body': 'Internal server error: Error getting speaker labels'
    #     }
    # logger.info(f"Spearker labels: {speaker_labels}")
    speaker_formatted_content = format_content(json_data)
    if speaker_formatted_content == "":
        logger.error("Error formatting content")
        return {
            'statusCode': 500,
            'body': 'Internal server error: Error formatting content'
        }
    logger.info(f"Formatted content: {speaker_formatted_content}")

    # Create an Amazon Bedrock client
    try:
        config = Config( # https://github.com/boto/boto3/issues/2424
            read_timeout=900,
            connect_timeout=900,
            retries={"max_attempts": 0}
        )
        bedrock_client = boto3.client('bedrock-runtime', config=config)
        logger.info("Amazon Bedrock client created")
    except Exception as e:
        logger.error(f"Error creating Amazon Bedrock client: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error creating Amazon Bedrock client: {e}'
        }
    
    # Use the provided instructions to provide the summary. Use a default if no intructions are provided.
    SUMMARY_INSTRUCTIONS = os.getenv('SUMMARY_INSTRUCTIONS',instructions.get_instructions(language_code))
    logger.info(f"SUMMARY_INSTRUCTIONS: {SUMMARY_INSTRUCTIONS}")
    
    # Use the provided model ID to invoke the model.
    try:
        BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    except KeyError:
        logger.error("Error getting BEDROCK_MODEL_ID")
        return {
            'statusCode': 500,
            'body': 'Internal server error: Error getting BEDROCK_MODEL_ID'
        }
    logger.info(f"BEDROCK_MODEL_ID: {BEDROCK_MODEL_ID}")

    # Launch the bedrock to analyze the json_data to detect who is the agent and who is the customer, the customer sentiment and the agent quality
    try:
        # Create the payload to provide to the Anthropic model.
        messages = [{ "role":"user", "content":[{"type":"text","text": SUMMARY_INSTRUCTIONS + "\n" + 
                                                 "<transcribe>\n" + speaker_formatted_content + "</transcribe>"}]}]

        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "temperature": 0,
                "top_p": 1.
            }
        )

        start_time = time.time()
        response = bedrock_client.invoke_model(body=body, modelId=BEDROCK_MODEL_ID)
        end_time = time.time()
        logger.info(f"Bedrock total time spent thinking: {round(end_time - start_time, 2)}s")

        logger.debug(response)

    except Exception as e:
        logger.error(f"Error analyzing transcript: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error analyzing transcript: {e}'
        }
    
    # Decode the response from the Anthropic model
    try:
        analyzer_response = json.loads(response.get('body').read())
        logger.info(f'analyzer_response: {analyzer_response}')
    except Exception as e:
        logger.error(f"Error decoding analyzer response: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error decoding analyzer response: {e}'
        }

    # Save the response value in S3.
    try:
        obj = s3.Object(output_s3_bucket, output_s3_key)
        obj.put(Body=analyzer_response['content'][0]['text'] + "\n\n4. Original Call Transcribe" + speaker_formatted_content)
    except Exception as e:
        logger.error(f"Error saving analyzer response: {e}")
        return {
            'statusCode': 500,
            'body': f'Internal server error: Error saving analyzer response: {e}'
        }
    logger.info(f"Response saved in s3://{output_s3_bucket}/{output_s3_key}")

    return {
        'statusCode': 200,
        'body': 'OK'
    }


def send_notification(subject: str, message: str) -> dict:
    # Send the text to the SNS topic
    sns = boto3.client('sns')
    sns_topic_arn = os.getenv('OUTPUTNOTIFICATIONTOPIC_TOPIC_ARN')
    
    # For local run
    if sns_topic_arn == 'OutputNotificationTopic':
        sns_topic_arn = 'arn:aws:sns:eu-central-1:613695894342:call-center-analyzer-notification-topic-613695894342'
    logger.info(f"SNS topic ARN: {sns_topic_arn}")
    
    if sns_topic_arn:
        try:
            sns.publish(TopicArn=sns_topic_arn, Message=message, Subject=subject[:100])
            logger.info(f"Text sent to SNS topic: {sns_topic_arn}")
            return {
                'statusCode': 200,
                'body': 'OK'
            }
        except Exception as e:
            logger.error(f"Error sending text to SNS topic: {e}")
            return {
                'statusCode': 500,
                'body': f'Internal server error: Error sending text to SNS topic: {e}'
            }
        
    else:
        logger.error("OUTPUTNOTIFICATIONTOPIC_TOPIC_ARN not set")
        return {
            'statusCode': 500,
            'body': 'Internal server error: OUTPUTNOTIFICATIONTOPIC_TOPIC_ARN not set'
        }
        

def notify(input_s3_bucket: str, input_s3_key: str) -> dict:
    # Verify if it is an txt file
    if not input_s3_key.endswith(OUTPUT_EXT):
        logger.warning(
            f"Invalid file type: s3://{input_s3_bucket}/{input_s3_key}")
        return {
            'statusCode': 400,
            'body': 'Invalid file type'
        }
    logger.info(f"Notifying file: s3://{input_s3_bucket}/{input_s3_key}")

    # Generate the original input file name
    original_input_s3_key = input_s3_key.replace(OUTPUT_DIR, "", 1).replace(OUTPUT_EXT, TRANSCRIBE_EXT)
    logger.info(f"Original input file name: s3://{input_s3_bucket}/{original_input_s3_key}")

    # Read the input txt file from s3
    try:
        s3 = boto3.resource('s3')
        msg = s3.Object(input_s3_bucket, input_s3_key)
        text = msg.get()['Body'].read().decode('utf-8')
        response = send_notification(f"Call Center Analyzer - {input_s3_key}", text)
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        response = {
            'statusCode': 500,
            'body': f'Internal server error: Error reading input file: {e}'
        }
    finally:
        return response


def handler(event, context):
    # Retrieve the S3 bucket and object information from the event
    try:
        event_name = event['Records'][0]['eventName']
        input_s3_bucket = event['Records'][0]['s3']['bucket']['name']
        input_s3_key = event['Records'][0]['s3']['object']['key']
    except KeyError:
        logger.warning(f"Invalid event data {event}")
        return {
            'statusCode': 400,
            'body': 'Invalid event data'
        }
    logger.debug(event)

    # Process the file based on the directory
    if event_name in handled_event_names:
        if input_s3_key.startswith(TRANSCRIBE_DIR):
            response = transcribe(input_s3_bucket, input_s3_key)
        elif input_s3_key.startswith(ANALYZE_DIR):
            response = analyze(input_s3_bucket, input_s3_key)
        elif input_s3_key.startswith(OUTPUT_DIR):
            response = notify(input_s3_bucket, input_s3_key)
        else:
            logger.warning(
                f"Invalid file path: s3://{input_s3_bucket}/{input_s3_key}")
            return {
                'statusCode': 400,
                'body': 'Invalid file path'
            }
    else:
        logger.info(f"This is {event_name} and is not ObjectCreated:Put event")
        return {
            'statusCode': 200,
            'body': 'Skipped'
        }

    if response['statusCode'] != 200:
        send_notification(f"Error processing file: s3://{input_s3_bucket}/{input_s3_key}", f"status code {response['statusCode']}/n{response['body']}")
        return response
        
    return response
