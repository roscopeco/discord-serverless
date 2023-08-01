## Utility library for serverless Discord apps

This is a (currently very simple) library that eases development of serverless Discord
app and bots.

Currently, it targets AWS Lambda only, and provides a decorator and some utility
functions that make discord signature verification and ping handling automatic.

I will grow it with things I end up needing in my work, but if you have different
needs and want to extend the library to support them, then PRs would be gratefully
received!

### MVP Example

This will accept any slash command you've configured for your bot, and just greet 
the user who calls it, tagging them in the reply. 

```python
from discord_serverless import discord_command_lambda, discord_command_response

@discord_command_lambda(discord_key=YOUR_PUBLIC_KEY)
def command_handler(payload):
    return discord_command_response(4, f'Hi there <@{payload["member"]["user"]["id"]}>')
```

### General usage

#### AWS (Tested)

> **Note**: If using with API Gateway, you'll need to set up proxy integration.
> Failing to do this will likely lead to none of the requests from Discord passing
> signature verification, which is based on the raw original payload.
> 
> This _shouldn't_ be a problem if you're using function URLs (but I still don't recommend
> that for reasons that are way beyond the scope of this README 😅).

For AWS, simply create a handler function that takes a single `payload` argument,
and decorate it with `discord_command_lambda` decorator. You need to pass in the
Discord public key for your application, e.g:

```python
@discord_command_lambda(discord_key=YOUR_PUBLIC_KEY)
def command_handler(payload):
    # ... do stuff ...
```

This function should return a regular AWS response (compatible with your chosen 
integration) with the payload format outlined in the Discord interaction webhook
docs.

The payload that gets passed in is the standard Discord interaction payload.

To check the actual slash command that was called (in case you have a single bot 
doing multiple commands), look in `payload["data"]["name"]`.

If your command supports options, you'll find them in a list of dicts under
`payload["data"]["options"]` with entries like:

```python
{
 "name": "the option name",
 "value": "the value, appropriately typed" 
}
```

See [Example Interaction](https://discord.com/developers/docs/interactions/application-commands#slash-commands-example-interaction)
in the Discord docs for full layout.

There are a couple of helper functions for responses:

* `discord_command_response` - Create a regular success response. Response type `4`
  will send the `content` you supply as the reply message to the user.
* `discord_unknown_command_response` - Create an error response. This will get sent
  as a HTTP 400, and will cause discord to display "The interaction failed" to the
  the user (but _only_ the user - not the rest of the channel).

For help with the interaction response types, see [Responding to an interaction](https://discord.com/developers/docs/interactions/receiving-and-responding#responding-to-an-interaction)
in the Discord docs.

#### Other Cloud Providers

Things will be a bit more manual here (but I'll happily add comfort wrappers if
there's enough call and a PR that contributes them 😉).

The easiest thing to do is use the `discord_command_webhook` decorator, which 
is similar to the `lambda` one above but needs you pass in a couple of `Callable`s
the code will use to get access to the data in a provider-specific way.

You could also go full manual mode and directly call `discord_verify_signature` and
`handle_discord_command`, passing things in as appropriate - this is how the decorator
works under the hood and gives you full flexibility if that's your thing.

Take a look at the code in `discord_serverless.py` for examples to get you started.

### Developing

Don't forget to set up `pre-commit` if you're developing things, especially if you
plan to push a PR.

### Legal Mumbo-Jumbo

Copyright (c)2023 Ross Bamford (and contributors)

License: MIT (see `LICENSE.md` for details).
