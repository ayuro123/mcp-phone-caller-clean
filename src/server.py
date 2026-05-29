#!/usr/bin/env python3
import os

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

from fastmcp import FastMCP
from twilio.rest import Client

mcp = FastMCP("Sample MCP Server")

BASE_URL = "https://fastmcp-server-cy6x.onrender.com"
ELEVENLABS_VOICE_ID = "M6ic45wruJGWAxLFEMNK"


def generate_audio(message: str, filename: str) -> str:
    api_key = os.environ["ELEVENLABS_API_KEY"]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    response = requests.post(
        url,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": message[:800],
            "model_id": "eleven_multilingual_v2",
        },
        timeout=30,
    )

    if response.status_code != 200:
        print("ElevenLabs error status:", response.status_code)
        print("ElevenLabs error body:", response.text)
        response.raise_for_status()

    audio_path = f"/tmp/{filename}"

    with open(audio_path, "wb") as f:
        f.write(response.content)

    return audio_path


def place_call(to_number: str, message: str, audio_filename: str) -> None:
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]

    client = Client(account_sid, auth_token)

    generate_audio(message, audio_filename)

    audio_url = f"{BASE_URL}/audio/{audio_filename}"

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Play>{audio_url}</Play></Response>"
    )

    client.calls.create(
        to=to_number,
        from_=from_number,
        twiml=twiml,
    )


@mcp.tool(description="Greet a user by name with a welcome message from the MCP server")
def greet(name: str) -> str:
    return f"Hello, {name}! Welcome to our sample MCP server running on Render!"


@mcp.tool(description="Get information about the MCP server including name, version, environment, and Python version")
def get_server_info() -> dict:
    return {
        "server_name": "Sample MCP Server",
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": os.sys.version.split()[0],
    }


@mcp.tool
def call_me(message: str) -> str:
    to_number = os.environ["MY_PHONE_NUMBER"]
    place_call(to_number, message, "call_me.mp3")
    return "Call placed"


@mcp.tool
def call_my_wife(message: str) -> str:
    to_number = os.environ["WIFE_PHONE_NUMBER"]
    place_call(to_number, message, "call_my_wife.mp3")
    return "Called wife"


mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(lifespan=mcp_app.lifespan, routes=[*mcp_app.routes])


@app.get("/health")
def health():
    return "ok"


@app.get("/warm")
def warm():
    _ = os.environ.get("TWILIO_ACCOUNT_SID", "")
    _ = os.environ.get("TWILIO_AUTH_TOKEN", "")
    _ = os.environ.get("TWILIO_FROM_NUMBER", "")
    _ = os.environ.get("ELEVENLABS_API_KEY", "")
    return "ok"


@app.get("/audio/{filename}")
def serve_audio(filename: str):
    return FileResponse(f"/tmp/{filename}", media_type="audio/mpeg")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    uvicorn.run(app, host=host, port=port)
