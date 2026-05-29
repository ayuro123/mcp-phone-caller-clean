#!/usr/bin/env python3
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

from fastmcp import FastMCP
from twilio.rest import Client
from elevenlabs.client import ElevenLabs

mcp = FastMCP("Sample MCP Server")

BASE_URL = "https://fastmcp-server-cy6x.onrender.com"
ELEVENLABS_VOICE_ID = "v0eRobr4pSbFT9FKocdw"


def generate_audio(message: str, filename: str) -> str:
    eleven = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    audio = eleven.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=message[:800],
        output_format="mp3_44100_128",
    )

    audio_path = f"/tmp/{filename}"

    with open(audio_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

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
    """Call my phone and read the message aloud using ElevenLabs."""
    to_number = os.environ["MY_PHONE_NUMBER"]
    place_call(to_number, message, "call_me.mp3")
    return "Call placed"


@mcp.tool
def call_my_wife(message: str) -> str:
    """Call my wife and read the message aloud using ElevenLabs."""
    to_number = os.environ["WIFE_PHONE_NUMBER"]
    place_call(to_number, message, "call_my_wife.mp3")
    return "Called wife"


# --- HTTP apps (FastAPI + MCP) ---

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
