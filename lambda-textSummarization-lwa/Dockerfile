# Use AWS Base Image
FROM public.ecr.aws/docker/library/python:3.12.0-slim-bullseye

# Use the Lambda Web Adaptor as an extension
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Change the invoke mode to RESPONSE_STREAM (default is BUFFERED)
ENV AWS_LWA_INVOKE_MODE=RESPONSE_STREAM

# Install pip requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy function code
COPY bedrock_caller.py ${LAMBDA_TASK_ROOT}
COPY main.py ${LAMBDA_TASK_ROOT}

# Set the CMD to the server Python script
CMD ["python", "main.py"]