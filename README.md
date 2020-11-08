# Chaturbate interface for Buttplug

Scrapes a Chaturbate websockets chat room for tip messages, forwarding them to your own vibrator.

I can only verify with Lovense toys, but it probably works for any vibrator Buttplug supports.

## Pull Requests are welcome!

To do (not really in order):

  - [ ] Recording tips to file for later parsing to Syncydink-compatible formats
  - [ ] Clean up the code (break into files/classes/functions)
  - [ ] Command-line options for log level and recording
  - [ ] Comment the code
  - [ ] Refactor to `asyncio` everything instead of threads (performance?)
  - [ ] Write a real schema for `levels.json`
  - [x] Get real logging
  - [ ] Support multiple vibrator devices
  - [ ] Support non-vibrator devices

## Setup and dependencies

Packages:
  - `python-readchar` (and see [this issue](https://github.com/magmax/python-readchar/issues/42) for a performance fix)
  - `buttplug`

## Specifying levels in levels.json

Description:

  - An object where each key is the username (also the URL path)
  - Each user is an array of level objects
  - The first matching level will be used. The recommended order of "type"s is "e" before "g", and "level"s without "time" (in order "x", "r", "c") before ones with "time" (in order of "value" from highest to lowest).
  - If a username is not found, "default" will be used

Level object:

  - Must include a "type" string for the type of comparison to be made with "value"
    - "g" for greater than or equal to
    - "e" for equal to
  - Must include a "value" integer for tip value to be compared to
  - Must include a "level" string to describe the action taken on match
    - Values requiring a "time" integer:
      - "0" for off (useful for pause)
      - "L" for low
      - "M" for medium
      - "H" for high
      - "U" for ultra
    - Other values:
      - "x" for raise exception (useful for WIP users)
      - "c" for clear queue
      - "r" for random, requires "selection" array of integers for a "value" to choose. Must be specified before the levels in "selection".

Example:

```json
{
    "default": [
        {"type": "e", "value": 255, "level": "r", "selection": [1, 1, 1, 100, 250]}
        {"type": "e", "value": 250, "time": 30, "level": "pulse"},
        {"type": "g", "value": 100, "time": 20, "level": "M"},
        {"type": "g", "value": 1, "time": 1, "level": "L"}
    ]
}
```
****