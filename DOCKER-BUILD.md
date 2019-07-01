# Build using Docker

1. Make sure docker and docker-compose are installed
2. Use docker-compose to build rpms for the various distros
```
make clean
docker-compose build --parallel
docker-compose up
```
3. RPMs are in rpm-build/
