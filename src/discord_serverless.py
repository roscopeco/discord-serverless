# Discord helpers for a serverless (currently AWS lambda) environment
#
# Copyright (c)2023 Ross Bamford (and contributors)
# MIT license
#
import json
from typing import Callable, Any

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError


def discord_command_lambda(discord_key: str):
    """Decorator for an AWS lambda function handler that processes Discord webhook interactions

    Apply this to a top-level function that takes a single `payload` argument (expect type `dict[str, Any]`).
    The decorator will verify the Discord signature, handle pings, and for actual commands will deserialize the
    interaction payload into that parameter.

    The function should return a standard return type for your chosen Lambda integration, and  can then be
    configured directly in AWS as the lambda handler.

    :param discord_key: [:class:`str`] Public key for your Discord application.
    """
    return discord_command_webhook(
        discord_key,
        lambda name, args: args[0]["headers"].get(name),
        lambda args: args[0]["body"],
        lambda args: json.loads(args[0]["body"]),
    )


def discord_command_webhook(
    discord_key: str,
    extract_header: Callable[[str, tuple[Any, ...]], str],
    extract_raw_payload: Callable[[tuple[Any, ...]], str],
    extract_payload: Callable[[tuple[Any, ...]], dict[str, Any]],
):
    """Decorator for a generic serverless function handler that processes Discord webhook interactions

    Apply this to a top-level function that takes a single `payload` argument (expect type `dict[str, Any]`).
    The decorator will verify the Discord signature, handle pings, and for actual commands will deserialize the
    interaction payload into that parameter. You must provide Callables that will extract headers and payload
    from whatever form the standard arguments to a python handler on your particular cloud take.

    The function should return a standard return type for your chosen cloud's function integration, and can then be
    configured directly as the handler in your cloud-specific configuration.

    :param discord_key: [:class:`str`] Public key for your Discord application.
    :param extract_header: Callable that extracts a named header from your handler's input arguments
    :param extract_raw_payload: Callable that extracts the raw payload from your handler's input arguments (for signature verification)
    :param extract_payload: Callable that extracts the deserialized payload from your handler's input arguments
    """

    def decorator(base_handler):
        def handler(*args):
            # Discord sends an X-Signature-Ed25519 and X-Signature-Timestamp in header
            is_valid = discord_verify_signature(
                discord_key,
                extract_header("x-signature-ed25519", args),
                extract_header("x-signature-timestamp", args),
                extract_raw_payload(args),
            )

            if not is_valid:
                return {"statusCode": 401, "body": "Invalid request signature"}

            return handle_discord_command(extract_payload(args), base_handler)

        return handler

    return decorator


def handle_discord_command(
    payload: dict[str, Any], base_handler: Callable[[dict[str, Any]], dict[str, Any]]
):
    """Handle a Discord interaction slash command, taking care of boilerplate ping requests and the like.

    Valid slash commands will be passed to the `base_handler`.

    Generally you won't need to call this directly as it's called by decorated handlers automatically, but
    it's here if you want to do a custom flow.

    :param payload: Deserialized payload from your handler's input arguments
    :param base_handler: Callable that will handle actual slash commands.
    """
    command_type = payload["type"]

    if command_type == 1:
        # Discord ping - just behave expectedly...
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": '{ "type": 1 }',
        }
    elif command_type == 2:
        # Slash command - let's do this!
        return base_handler(payload)
    else:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(f"unhandled request type: {command_type}"),
        }


def discord_command_response(
    interaction_callback_type: int, content: str
) -> dict[str, Any]:
    """Generate a slash command interaction response for Discord.

    :param interaction_callback_type: See https://discord.com/developers/docs/interactions/receiving-and-responding#responding-to-an-interaction
    :param content: Content to send back (often, the message for the user)
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(
            {"type": interaction_callback_type, "data": {"content": content}}
        ),
    }


def discord_unknown_command_response(command: str) -> dict[str, Any]:
    """Generate a generic "unknown command" response for Discord.

    :param command: Command to parrot in the response error message
    """
    return {"statusCode": 400, "body": json.dumps(f"Unknown command: {command}")}


def discord_verify_signature(
    public_key: str, signature: str, timestamp: str, raw_payload: str
) -> bool:
    message = timestamp + raw_payload
    verify_key = VerifyKey(bytes.fromhex(public_key))

    try:
        verify_key.verify(message.encode(), signature=bytes.fromhex(signature))
        return True
    except BadSignatureError as e:
        print("invalid request signature", e)
        return False
