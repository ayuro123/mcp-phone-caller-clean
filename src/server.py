#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from twilio.rest import Client
from xml.sax.saxutils import escape

mcp = FastMCP("Sample MCP Server")

@mcp.tool(description="Greet a user by name with a welcome message from the MCP server")
def greet(name: str) -> str:
    return f"Hello, {name}! Welcome to our sample MCP server running on Heroku!"

@mcp.tool(description="Get information about the MCP server including name, version, environment, and Python version")
def get_server_info() -> dict:
    return {
        "server_name": "Sample MCP Server",
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": os.sys.version.split()[0]
    }

@mcp.tool
def call_me(message: str) -> str:
    """Call my phone and read the message aloud."""
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    to_number = os.environ["MY_PHONE_NUMBER"]

    client = Client(account_sid, auth_token)

    text = escape(message)[:800]
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="alice">{text}</Say></Response>'

    client.calls.create(
        to=to_number,
        from_=from_number,
        twiml=twiml,
    )

    return "Call placed"
@mcp.tool
def call_my_wife(message: str) -> str:
    """Call my wife and read the message aloud."""
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    to_number = os.environ["WIFE_PHONE_NUMBER"]

    client = Client(account_sid, auth_token)

    text = escape(message)[:800]
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="alice">{text}</Say></Response>'

    client.calls.create(
        to=to_number,
        from_=from_number,
        twiml=twiml,
    )

    return "Called wife"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting FastMCP server on {host}:{port}")
    
    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )
