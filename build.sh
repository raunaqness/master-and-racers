#!/bin/sh

docker build -f dockerfile-master -t master .
docker build -f dockerfile-racer -t racer .
