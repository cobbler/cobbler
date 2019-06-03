# Tests

## Running in a dedicated environment

Before running tests, ensure you have installed `requirements-tests.txt`.

To run tests:

  - Ensure you have pytest installed.
  - Ensure you have a running cobbler instance which is setup correctly.
  - From the directory tests/ execute `pytest` if you want to run all tests.

Note that these tests require modifications to a running Cobbler server. They
will attempt to clean up any test objects created, but it may be best to not
execute these against a production Cobbler server.

## Running in Docker

Run: `docker build -t cobbler . && docker run -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name cobbler --privileged cobbler`

After executing the command you should grab a mug and wait for the result. Building the image is quite time consuming.

## Helping

The tests are currently in a very poor state and we only fixed the most critical integration tests to ensure that
cobbler is running and the api is not broken.
