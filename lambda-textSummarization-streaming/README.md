# Purpose

The purpose of this document is to document a number of the lessons learnt from the effort to enable response streaming in AWS Lambda functions (using function URLs) written in Python. and integrate that into an AWS Gateway . 

This documentation is done in the hopes that the same mistakes / meanderings will not have to be made to achieve the outcome stated in the paragraph above. 

As of Aug 2024 (and to the best of the author's knowledge), the information contained within this document is accurate.  

# Docker Images

- TODO: Talk about Using SHA instead of Tags to deploy ECR images to Lambda

# Lambdas

- TODO: Talk about changing the InvokeMode of the Lambda to RESPONSE_STREAM

# APIGateway

## Getting APIGateway to Stream from a Lambda function URL

> THIS DOES NOT WORK. THE `Transfer-Encoding: chunked` HEADER DISAPPEARS FOR SOME REASON AFTER PASSING THROUGH APIGATEWAY

The APIGateway REST API will simply pass the streamed response from a Lambda function URL if

1. The integration is HTTP Proxy (have yet to try HTTP Non-Proxy integration) to the function URL, and
2. the streamed response contains the header `Transfer-Encoding: chunked`. 

> TODO: Test HTTP/Websocket API with HTTP integration

Note that APIGateway REST APIs are likely more favorable over APIGateway HTTP APIs, since the timeout of Regional REST APIs and Private REST APIs can be increased past 29 seconds. 
(see [this post](https://aws.amazon.com/about-aws/whats-new/2024/06/amazon-api-gateway-integration-timeout-limit-29-seconds/) and [this section of this writeup](#increasing-the-max-timeout-of-apigateway-rest-apis)). 

### Relevance to 

[This documentation](https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html) about Lambda invocation using function URL (see `Example output for a custom response`) tells us that for the response from the function URL to contain a custom header, we need to include that header in what is returned by our function URL. 



In other words, to achieve #2 in the section above (i.e. adding the `Transfer-Encoding` heading)

If using a 

## Increasing the Max Timeout of APIGateway REST APIs

When integrating higher-latency LLM services, there is a high chance that you will need to increase the timeout of your APIGateway REST API (which should be integrated via HTTP Proxy to your LLM-calling Lambda through its function URL)

TODO: FIGURE OUT HOW TO DO IT