import os, json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, ConfigDict
from typing import Optional
from bedrock_caller import lambda_handler

app = FastAPI()

class Event(BaseModel):
    model_config = ConfigDict(extra='allow')

    responseData: list
    category: str
    userInput: Optional[str] = ""
    previousSummary: Optional[str] = ""


@app.post("/")
def api_stream_response(request_body: Event):

    print("Received event: " + json.dumps(request_body.model_dump()))

    try:
        stream_generator = lambda_handler(request_body, None)
        response = StreamingResponse(stream_generator, media_type='text/plain')

    except Exception as e:
        print(str(e))
        return JSONResponse(
            status_code=500,
            content={
                "errorMessage": str(e)
            }
        )
    
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))