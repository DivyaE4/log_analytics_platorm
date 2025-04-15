#!/bin/bash

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
sleep 10

# Create topics
kafka-topics --create --bootstrap-server kafka:29092 --replication-factor 1 --partitions 3 --topic api-requests
kafka-topics --create --bootstrap-server kafka:29092 --replication-factor 1 --partitions 3 --topic api-responses
kafka-topics --create --bootstrap-server kafka:29092 --replication-factor 1 --partitions 3 --topic application-errors
kafka-topics --create --bootstrap-server kafka:29092 --replication-factor 1 --partitions 3 --topic system-logs

echo "Kafka topics created."

# List topics
kafka-topics --list --bootstrap-server kafka:29092