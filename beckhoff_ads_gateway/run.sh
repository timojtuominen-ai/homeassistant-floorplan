#!/usr/bin/with-contenv bashio
set -e

export PLC_IP="$(bashio::config 'plc_ip')"
export PLC_AMS_NET_ID="$(bashio::config 'plc_ams_net_id')"
export LOCAL_AMS_NET_ID="$(bashio::config 'local_ams_net_id')"
export PLC_ADS_PORT="$(bashio::config 'plc_ads_port')"
export POLL_INTERVAL="$(bashio::config 'poll_interval')"

export INDEX_GROUP="$(bashio::config 'index_group')"
export INDEX_OFFSET="$(bashio::config 'index_offset')"
export ADS_DATA_TYPE="$(bashio::config 'data_type')"
export VALUE_SCALE="$(bashio::config 'scale')"
export VALUE_OFFSET="$(bashio::config 'offset_adjustment')"
export VALUE_PRECISION="$(bashio::config 'precision')"

export ENTITY_NAME="$(bashio::config 'entity_name')"
export ENTITY_ID="$(bashio::config 'entity_id')"
export UNIT_OF_MEASUREMENT="$(bashio::config 'unit_of_measurement')"
export DEVICE_CLASS="$(bashio::config 'device_class')"
export STATE_CLASS="$(bashio::config 'state_class')"
export LOG_LEVEL="$(bashio::config 'log_level')"
export ADD_LOCAL_ROUTE="$(bashio::config 'add_local_route')"

export MQTT_HOST="$(bashio::services mqtt 'host')"
export MQTT_PORT="$(bashio::services mqtt 'port')"
export MQTT_USERNAME="$(bashio::services mqtt 'username')"
export MQTT_PASSWORD="$(bashio::services mqtt 'password')"

bashio::log.info "Starting Beckhoff ADS Gateway v0.3.5"
bashio::log.info "PLC ${PLC_IP}, AMS ${PLC_AMS_NET_ID}, ADS port ${PLC_ADS_PORT}"
bashio::log.info "Local AMS Net ID ${LOCAL_AMS_NET_ID}"
bashio::log.info "Direct memory read: IG=${INDEX_GROUP}, IO=${INDEX_OFFSET}, type=${ADS_DATA_TYPE}"
bashio::log.info "Scaling: value * ${VALUE_SCALE} + ${VALUE_OFFSET}"
bashio::log.info "Explicit local ADS route: ${ADD_LOCAL_ROUTE}"

exec /opt/venv/bin/python3 /app/main.py
