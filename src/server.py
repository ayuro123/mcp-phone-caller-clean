#!/usr/bin/env python3
import os
import uuid
from typing import Optional

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

from fastmcp import FastMCP
from twilio.rest import Client

mcp = FastMCP("Sample MCP Server")

BASE_URL = "https://fastmcp-server-cy6x.onrender.com"

DEFAULT_ELEVENLABS_VOICE_ID = "q7SLtRoVebhug4ZZZO9f"


def resolve_voice_id(voice: Optional[str] = None, voice_id: Optional[str] = None) -> str:
    api_key = os.environ["ELEVENLABS_API_KEY"]

    if voice_id:
        return voice_id.strip()

    if not voice:
        return DEFAULT_ELEVENLABS_VOICE_ID

    response = requests.get(
        "https://api.elevenlabs.io/v1/voices/search",
        headers={"xi-api-key": api_key},
        params={
            "search": voice,
            "page_size": 20,
        },
        timeout=30,
    )

    if response.status_code != 200:
        print("ElevenLabs voice search error status:", response.status_code)
        print("ElevenLabs voice search error body:", response.text)
        response.raise_for_status()

    voices = response.json().get("voices", [])

    if not voices:
        print(f"No ElevenLabs voice found for: {voice}")
        return DEFAULT_ELEVENLABS_VOICE_ID

    exact_matches = [
        v for v in voices
        if v.get("name", "").lower() == voice.lower()
    ]

    selected_voice = exact_matches[0] if exact_matches else voices[0]
    return selected_voice["voice_id"]


def generate_audio(
    message: str,
    filename: str,
    voice: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> str:
    api_key = os.environ["ELEVENLABS_API_KEY"]
    selected_voice_id = resolve_voice_id(voice=voice, voice_id=voice_id)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}"

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


def place_call(
    to_number: str,
    message: str,
    audio_filename: str,
    voice: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> None:
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]

    client = Client(account_sid, auth_token)

    generate_audio(
        message=message,
        filename=audio_filename,
        voice=voice,
        voice_id=voice_id,
    )

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


@mcp.tool(
    description=(
        "Call me with a spoken message. Optionally provide voice to search ElevenLabs "
        "by name, accent, style, or description, or provide an exact ElevenLabs voice_id."
    )
)
def call_me(
    message: str,
    voice: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> str:
    to_number = os.environ["MY_PHONE_NUMBER"]
    audio_filename = f"call_me_{uuid.uuid4().hex}.mp3"

    place_call(
        to_number=to_number,
        message=message,
        audio_filename=audio_filename,
        voice=voice,
        voice_id=voice_id,
    )

    return "Call placed"


@mcp.tool(
    description=(
        "Call my wife with a spoken message. Optionally provide voice to search ElevenLabs "
        "by name, accent, style, or description, or provide an exact ElevenLabs voice_id."
    )
)
def call_my_wife(
    message: str,
    voice: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> str:
    to_number = os.environ["WIFE_PHONE_NUMBER"]
    audio_filename = f"call_my_wife_{uuid.uuid4().hex}.mp3"

    place_call(
        to_number=to_number,
        message=message,
        audio_filename=audio_filename,
        voice=voice,
        voice_id=voice_id,
    )

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
