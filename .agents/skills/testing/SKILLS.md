---
name: testing
description: These are the guide lines when generating tests for the application.
---

# Testing

## Instructions
- every new feature must have a set of tests, 2 positive scenarios and 2 negative ones
- don't test functionality, but behaviour
- if already implemented functionalities are being modified, retest them after you do the changes
- if a test fails check the reason, there might be 2:
    - the implementation changed, in that case ask me first if this functionality should have indeed needed to changed, if I respond "yes" you can adapt the test to fit the new functionality, otherwise fix the implementation
    - external factors, like API keys missing, authentification could not be done properly etc. in these cases skip the tests and let me know

