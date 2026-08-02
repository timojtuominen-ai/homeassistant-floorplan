#!/usr/bin/env bashio
set -e

export PLC_IP="$(bashio::config 'plc_ip')"
export PLC_AMS_NET_ID="$(bashio::config 'plc_ams_net_id')"
export LOCAL_AMS_NET_ID="$(bashio::config 'local_ams_net_id')"
export PLC_ADS_PORT="$(bashio::config 'plc_ads_port')"
export POLL_INTERVAL="$(bashio::config 'poll_interval')"
export ADS_SYMBOL="$(bashio::config 'symbol')"
export ADS_DATA_TYPE="$(bashio::config 'data_type')"
export ENTITY_NAME="$(bashio::config 'entity_name')"
export ENTITY_ID="$(bashio::config 'entity_id')"
export LOG_LEVEL="$(bashio::config 'log_level')"

export MQTT_HOST="$(bashio::services mqtt 'host')"
export MQTT_PORT="$(bashio::services mqtt 'port')"
export MQTT_USERNAME="$(bashio::services mqtt 'username')"
export MQTT_PASSWORD="$(bashio::services mqtt 'password')"

bashio::log.info "Starting Beckhoff ADS Gateway"
bashio::log.info "PLC: ${PLC_IP}, AMS Net ID: ${PLC_AMS_NET_ID}, ADS port: ${PLC_ADS_PORT}"
bashio::log.info "Local AMS Net ID: ${LOCAL_AMS_NET_ID}"
bashio::log.info "Symbol: ${ADS_SYMBOL} (${ADS_DATA_TYPE})"
bashio::log.info "MQTT service: ${MQTT_HOST}:${MQTT_PORT}"

exec /opt/venv/bin/python3 /app/main.py
