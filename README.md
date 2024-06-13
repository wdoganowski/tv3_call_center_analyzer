# Call Center Analyzer

Use the Amazon Transcribe to prepare the transcription of the call and the Berdock with `Anthropic Claude 3 Sonnet` model to prepare the tranlation and analyzis.

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

## Preparation

In `template.yml` change `Environment` and `Owner` parameters.

## Building

```sh
sam build
```

## Testing

Update the `events\` and `environments\` json files with the arns of your test resources and runn the following:

``` sh
sam local invoke AnalyzeFunction --event events/analyze.json --env-vars environments/dev.json
sam local invoke AnalyzeFunction --event events/transcribe.json --env-vars environments/dev.json
sam local invoke AnalyzeFunction --event events/notify.json --env-vars environments/dev.json
```

## Deploy

```sh
sam deploy --parameter-overrides Owner={your-email-address}
```

## Additional configuration

1. Request access to `Anthropic Claude 3 Sonnet` Amazon Bedrock base model.
2. Optionally, configure the AppFlow to copy the files from the source (e.g. SharePoint) to the S3 bucket.

## Environemnt Variables

The process may be modified using environemnt variables:

1. `SUMMARY_INSTRUCTIONS` Modify the instruction
2. `BEDROCK_MODEL_ID` Modify the Amazon Medrock base model
3. `OUTPUTNOTIFICATIONTOPIC_TOPIC_ARN` Modify the SNS topic
