# Call Center Analyzer

Use the Amazon Transcribe to prepare the transcription of the call and the Bedrock with `Anthropic Claude 3 Sonnet` model to prepare the translation and analyses.

The Bedrock is prompted with following instruction:

```txt
You are responsible for translating the conversation of the call center agent
of the OTT video service called Go3 with a customer.
You need to provide all the answers in English.

The Transcribe service generates the conversation and is provided in the following format:

<transcribe>
time_stamp  speaker_label   text
time_stamp  speaker_label   text
</transcribe>

1. Summarize the conversation and analyze the customer sentiment and the agent quality. Provide the summary and analyses in English.
Label it "1. Sentiment and Quality Analysis:"

2. Analyze the speakers and decide who the agent and customer are. Note that there may be more than one customer speaking.
Label it "2. Speaker Analysis:"

3. Analyze the conversation made in {language_code} and translate it to English so it makes sense.
Provide translated conversation with labels changed to "Customer" and "Agent."
Include the original time stamps.
Label it "3. Translated Conversation:"
```

The result is set to the SNS topic.

## S3 Bucket Structure

The following directory structure is created in the S3 bucket:

- `recordings/` - The input directory for the mp3 files with the recordings
- `transcribes/` - The directory with the json file with the Amazon Transcribe results
- `output/` - The directory with the translation and analyses ready for sending out

Further explanation is available here in [the article describing this project](thttps://github.com/wdoganowski/cloud-chronicles/tree/95af666925520705a2e2334e373639128f09cd8a/08.%20Transforming%20Call%20Center%20Analytics%20with%20AWS%20Bedrock).

## Preparation

In `template.yml` change `Environment` and optionally set the `Owner` parameter.

## Building

```sh
sam build
```

## Testing

Update the `events\` and `environments\` json files with the ARNs of your test resources and rnn the following:

``` sh
sam local invoke AnalyzeFunction --event events/analyze.json --env-vars environments/dev.json
sam local invoke AnalyzeFunction --event events/transcribe.json --env-vars environments/dev.json
sam local invoke AnalyzeFunction --event events/notify.json --env-vars environments/dev.json
```

## Deploy

If the `Owner` parameter has no default value, you need to specify it here:

```sh
sam deploy --parameter-overrides Owner={your-email-address}
```

Otherwise just deploy without any parameters:

```sh
sam deploy
```

## Additional configuration

1. Request access to `Anthropic Claude 3 Sonnet` Amazon Bedrock base model.
2. Optionally, configure the AppFlow to copy the files from the source (e.g. SharePoint) to the S3 bucket.

## Environemnt Variables

The process may be modified using environment variables:

1. `SUMMARY_INSTRUCTIONS` Modify the instruction
2. `BEDROCK_MODEL_ID` Modify the Amazon Bedrock base model
3. `OUTPUTNOTIFICATIONTOPIC_TOPIC_ARN` Modify the SNS topic
