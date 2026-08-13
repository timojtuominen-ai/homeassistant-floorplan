#!/usr/bin/env python3
import json, logging, os, re, socket, threading, time
from pathlib import Path

import paho.mqtt.client as mqtt
import pyads

OPT = json.loads(Path("/data/options.json").read_text())
ENT = json.loads(Path("/app/entities.json").read_text())

PLC_IP = OPT["plc_ip"]
PLC_AMS = OPT["plc_ams_net_id"]
LOCAL_AMS = OPT["local_ams_net_id"]
ADS_PORT = int(OPT.get("plc_ads_port", 851))
POLL = float(OPT.get("poll_interval", 1.0))
RECONNECT = int(OPT.get("reconnect_delay", 5))
PULSE = int(OPT.get("command_pulse_ms", 200)) / 1000.0
TEST = bool(OPT.get("test_mode", True))
DISCOVERY = bool(OPT.get("publish_discovery", True))

MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

logging.basicConfig(level=getattr(logging, OPT.get("log_level", "INFO")),
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("beckhoff_tc3_gateway")

PREFIX = "beckhoff_tc3_test" if TEST else "beckhoff_cx5000"
DEVICE_NAME = "Beckhoff CX9240 TEST" if TEST else "Beckhoff CX9240"
DEVICE_ID = "beckhoff_cx9240_test" if TEST else "beckhoff_cx5000"

ads_lock = threading.Lock()
plc = None
mqttc = None
command_map = {}
symbol_cache = {}
symbol_prefix = ""

# MQTT Discovery IDs used by gateway v0.2.0/v0.2.1 for the same 15 fire detectors.
# v0.2.2 restored the original auto_xfire_* IDs used by the existing HA dashboard.
# Home Assistant keeps retained MQTT discovery configs, so without explicitly deleting
# these old IDs both generations appear as duplicate fire detector entities.
OBSOLETE_FIRE_DISCOVERY_IDS = [
    "fire_01_talli",
    "fire_02_liiteri",
    "fire_03_autotalli",
    "fire_04_tuulikaappi",
    "fire_05_eteinen",
    "fire_06_khh",
    "fire_07_tyohuone",
    "fire_08_kellari",
    "fire_09_kellarin_varasto",
    "fire_10_tekninen_tila",
    "fire_11_makuuhuone_lt",
    "fire_12_keittio",
    "fire_13_olohuone",
    "fire_14_emma",
    "fire_15_allu",
]


def obj_id(legacy):
    return ("tc3_test_" + legacy) if TEST else legacy


def topic_base(domain, legacy):
    return f"{PREFIX}/{domain}/{obj_id(legacy)}"


def discovery_topic(domain, legacy):
    return f"homeassistant/{domain}/{DEVICE_ID}/{obj_id(legacy)}/config"


def device():
    return {"identifiers": [DEVICE_ID], "name": DEVICE_NAME,
            "manufacturer": "Beckhoff", "model": "CX9240 / TwinCAT 3",
            "sw_version": "Kotiautomaatio_TC3 v0.29.6"}


def clear_symbol_cache():
    symbol_cache.clear()


def full_symbol_name(name):
    if symbol_prefix and not name.lower().startswith(symbol_prefix.lower()):
        return symbol_prefix + name
    return name


def log_symbol(sym, prefix="ADS symbol"):
    log.info("%s: name=%s type=%s size=%s index_group=%s index_offset=%s",
             prefix,
             getattr(sym, "name", None),
             getattr(sym, "symbol_type", getattr(sym, "symtype", None)),
             getattr(sym, "size", None),
             getattr(sym, "index_group", None),
             getattr(sym, "index_offset", None))


def resolve_symbol(name):
    sym = symbol_cache.get(name)
    if sym is not None:
        return sym
    actual = full_symbol_name(name)
    sym = plc.get_symbol(actual)
    symbol_cache[name] = sym
    log_symbol(sym, "ADS symbol resolved")
    return sym


def read_symbol(name):
    with ads_lock:
        return resolve_symbol(name).read()


def write_symbol(name, value):
    with ads_lock:
        resolve_symbol(name).write(value)


def pulse_symbol(symbol):
    write_symbol(symbol, True)
    time.sleep(PULSE)
    write_symbol(symbol, False)


def publish_config(domain, legacy, name, state_topic, extra=None, command_topic=None):
    cfg = {
        "name": name,
        "object_id": obj_id(legacy),
        "unique_id": f"{DEVICE_ID}_{obj_id(legacy)}",
        "state_topic": state_topic,
        "availability_topic": f"{PREFIX}/availability",
        "payload_available": "online", "payload_not_available": "offline",
        "device": device(),
    }
    if command_topic:
        cfg["command_topic"] = command_topic
        cfg["payload_on"] = "ON"
        cfg["payload_off"] = "OFF"
    if extra:
        cfg.update(extra)
    mqttc.publish(discovery_topic(domain, legacy), json.dumps(cfg, ensure_ascii=False), retain=True)


def clear_obsolete_discovery():
    """Delete retained MQTT discovery configs for superseded duplicate fire entities."""
    for legacy in OBSOLETE_FIRE_DISCOVERY_IDS:
        mqttc.publish(discovery_topic("binary_sensor", legacy), "", retain=True)
        mqttc.publish(topic_base("binary_sensor", legacy) + "/state", "", retain=True)
    log.info("MQTT discovery cleanup: removed %d obsolete duplicate fire detector IDs",
             len(OBSOLETE_FIRE_DISCOVERY_IDS))


def subscribe_commands():
    if not mqttc or not mqttc.is_connected():
        return
    for topic in command_map:
        mqttc.subscribe(topic)


def setup_discovery():
    if not DISCOVERY or mqttc is None:
        return

    # Cleanup is intentionally repeated on every MQTT reconnect. Publishing an empty
    # retained config is idempotent and guarantees old duplicate entities disappear.
    clear_obsolete_discovery()

    for e in ENT["lights"]:
        legacy = e["legacy_object_id"]
        base = topic_base("light", legacy)
        publish_config("light", legacy, e["name"], base + "/state", command_topic=base + "/set")
        command_map[base + "/set"] = {"kind": "pulse_switch", "on": e["on_symbol"], "off": e["off_symbol"]}
    for e in ENT["sensors"]:
        legacy = e["legacy_object_id"]
        base = topic_base("sensor", legacy)
        extra = {"state_class": "measurement"}
        if e.get("unit"):
            extra["unit_of_measurement"] = e["unit"]
        if e.get("device_class") == "temperature":
            extra["device_class"] = "temperature"
        publish_config("sensor", legacy, e["name"], base + "/state", extra=extra)
    for e in ENT["binary_sensors"]:
        legacy = e["legacy_object_id"]
        base = topic_base("binary_sensor", legacy)
        extra = {"payload_on": "ON", "payload_off": "OFF"}
        if e.get("device_class"):
            extra["device_class"] = e["device_class"]
        publish_config("binary_sensor", legacy, e["name"], base + "/state", extra=extra)
    for e in ENT["switches"]:
        legacy = e["legacy_object_id"]
        base = topic_base("switch", legacy)
        publish_config("switch", legacy, e["name"], base + "/state", command_topic=base + "/set")
        command_map[base + "/set"] = {
            "kind": "pulse_switch" if e.get("pulse") else "direct_switch",
            "on": e["on_symbol"], "off": e["off_symbol"]
        }
    base = topic_base("binary_sensor", "gateway_online")
    publish_config("binary_sensor", "gateway_online", "TC3 Gateway online", base + "/state",
                   extra={"payload_on": "ON", "payload_off": "OFF", "device_class": "connectivity"})
    mqttc.publish(f"{PREFIX}/availability", "online", retain=True)
    subscribe_commands()
    log.info("MQTT discovery published: %d lights, %d sensors, %d binary sensors, %d switches",
             len(ENT["lights"]), len(ENT["sensors"]), len(ENT["binary_sensors"]), len(ENT["switches"]))


def on_connect(client, userdata, flags, reason_code, properties):
    log.info("MQTT connected: %s", reason_code)
    setup_discovery()


def on_message(client, userdata, msg):
    try:
        cmd = command_map.get(msg.topic)
        if not cmd:
            return
        val = msg.payload.decode().strip().upper()
        if val not in ("ON", "OFF"):
            return
        if cmd["kind"] == "pulse_switch":
            sym = cmd["on"] if val == "ON" else cmd["off"]
            threading.Thread(target=pulse_symbol, args=(sym,), daemon=True).start()
        else:
            sym = cmd["on"] if val == "ON" else cmd["off"]
            write_symbol(sym, val == "ON")
        log.info("Command %s -> %s", msg.topic, val)
    except Exception:
        log.exception("MQTT command failed")


def prepare_linux_ads_client():
    log.info("ADS client: opening local ADS port to set AMS Net ID")
    pyads.open_port()
    try:
        log.info("ADS client: setting local AMS Net ID to %s", LOCAL_AMS)
        pyads.set_local_address(LOCAL_AMS)
    finally:
        pyads.close_port()
    log.info("ADS client: local AMS Net ID configured")


def probe_ads_tcp():
    log.info("ADS network probe: testing %s:48898", PLC_IP)
    with socket.create_connection((PLC_IP, 48898), timeout=3.0):
        pass
    log.info("ADS network probe: TCP 48898 reachable")


def discover_symbol_prefix(p):
    global symbol_prefix
    log.info("ADS symbol discovery: uploading PLC symbol table")
    symbols = p.get_all_symbols()
    log.info("ADS symbol discovery: PLC returned %d symbols", len(symbols))

    matches = []
    exact_suffix_matches = []
    for sym in symbols:
        name = str(getattr(sym, "name", "") or "")
        lname = name.lower()
        if "xonline" in lname or "gvl_ha" in lname:
            matches.append(sym)
        if lname.endswith("gvl_ha.xonline"):
            exact_suffix_matches.append(sym)

    log.info("ADS symbol discovery: found %d xOnline/GVL_HA candidates", len(matches))
    for sym in matches[:100]:
        log_symbol(sym, "ADS candidate")
    if len(matches) > 100:
        log.info("ADS symbol discovery: %d additional candidates omitted", len(matches) - 100)

    if len(exact_suffix_matches) == 1:
        actual = str(exact_suffix_matches[0].name)
        suffix = "GVL_HA.xOnline"
        symbol_prefix = actual[:-len(suffix)] if actual.lower().endswith(suffix.lower()) else ""
        log.info("ADS symbol discovery: unique xOnline match=%s", actual)
        log.info("ADS symbol discovery: derived symbol prefix='%s'", symbol_prefix)
        return exact_suffix_matches[0]

    if len(exact_suffix_matches) > 1:
        log.error("ADS symbol discovery: multiple symbols end with GVL_HA.xOnline; refusing to guess")
    else:
        log.error("ADS symbol discovery: no symbol ending with GVL_HA.xOnline was found")
    raise RuntimeError("GVL_HA.xOnline ADS symbol name unresolved; inspect ADS candidate lines")


def slugify(value):
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "entity"


def friendly_tail(value):
    value = re.sub(r"^\d+_", "", value)
    text = value.replace("_", " ").strip()
    replacements = {
        "Keittio": "Keittiö", "keittio": "keittiö",
        "lampotila": "lämpötila", "Ulkolampotila": "Ulkolämpötila",
        "ulkolampotila": "ulkolämpötila"
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text[:1].upper() + text[1:] if text else value


def entity_exists(collection, key, value):
    return any(e.get(key) == value for e in ENT[collection])


def add_runtime_entity(collection, entry, unique_key):
    if entity_exists(collection, unique_key, entry[unique_key]):
        return False
    ENT[collection].append(entry)
    return True


def discover_runtime_entities(p):
    """Expand the test map from the actual TC3 symbol table without guessing nonexistent symbols."""
    log.info("ADS entity discovery: scanning TC3 symbol table for HA interface")
    symbols = p.get_all_symbols()
    names = {str(getattr(sym, "name", "") or "") for sym in symbols}

    def short_name(actual):
        if symbol_prefix and actual.lower().startswith(symbol_prefix.lower()):
            return actual[len(symbol_prefix):]
        return actual

    shorts = {short_name(name): name for name in names}
    short_lower = {name.lower(): name for name in shorts}
    added_lights = added_sensors = added_binary = 0

    for short in sorted(shorts):
        if short.startswith("GVL_HA.xLight_"):
            suffix = short[len("GVL_HA.xLight_"):]
            on = f"GVL_HA.xCmdLightOn_{suffix}"
            off = f"GVL_HA.xCmdLightOff_{suffix}"
            if on.lower() not in short_lower or off.lower() not in short_lower:
                log.warning("ADS entity discovery: skipping light %s because command pair is missing", short)
                continue
            entry = {
                "id": suffix.split("_", 1)[0],
                "slug": suffix,
                "state_symbol": short,
                "on_symbol": short_lower[on.lower()],
                "off_symbol": short_lower[off.lower()],
                "legacy_object_id": f"auto_light_{slugify(suffix)}",
                "name": friendly_tail(suffix),
            }
            if add_runtime_entity("lights", entry, "state_symbol"):
                added_lights += 1

        elif short.startswith("GVL_HA.rTemperature_"):
            suffix = short[len("GVL_HA.rTemperature_"):]
            entry = {
                "legacy_object_id": f"auto_temperature_{slugify(suffix)}",
                "name": friendly_tail(suffix),
                "symbol": short,
                "unit": "°C",
                "device_class": "temperature",
            }
            if add_runtime_entity("sensors", entry, "symbol"):
                added_sensors += 1

        else:
            binary_specs = (
                ("GVL_HA.xMotion_", "motion"),
                ("GVL_HA.xDoor_", "door"),
                ("GVL_HA.xFire_", "smoke"),
                ("GVL_HA.xLeakage_", "moisture"),
                ("GVL_HA.xLeak_", "moisture"),
                ("GVL_HA.xWater_", "moisture"),
            )
            for prefix, device_class in binary_specs:
                if short.startswith(prefix):
                    suffix = short[len(prefix):]
                    cls = device_class
                    if prefix == "GVL_HA.xFire_" and any(x in suffix.lower() for x in ("lampo", "heat")):
                        cls = "heat"
                    entry = {
                        "legacy_object_id": f"auto_{slugify(prefix.split('.')[-1].rstrip('_'))}_{slugify(suffix)}",
                        "name": friendly_tail(suffix),
                        "symbol": short,
                        "device_class": cls,
                        "invert": False,
                    }
                    if add_runtime_entity("binary_sensors", entry, "symbol"):
                        added_binary += 1
                    break

    log.info(
        "ADS entity discovery: added %d lights, %d temperature sensors, %d binary sensors; totals now %d/%d/%d/%d",
        added_lights, added_sensors, added_binary,
        len(ENT["lights"]), len(ENT["sensors"]), len(ENT["binary_sensors"]), len(ENT["switches"])
    )

    if added_lights or added_sensors or added_binary:
        setup_discovery()


def connect_ads():
    global plc, symbol_prefix
    log.info("ADS connect: preparing Linux client")
    prepare_linux_ads_client()
    probe_ads_tcp()
    log.info("ADS connect: opening PLC connection to %s / %s port %s (client route auto-created by pyads)",
             PLC_IP, PLC_AMS, ADS_PORT)
    p = pyads.Connection(PLC_AMS, ADS_PORT, PLC_IP)
    p.open()
    plc = p
    clear_symbol_cache()
    symbol_prefix = ""
    log.info("ADS connect: transport opened, trying GVL_HA.xOnline")
    try:
        online_sym = p.get_symbol("GVL_HA.xOnline")
        symbol_cache["GVL_HA.xOnline"] = online_sym
        log_symbol(online_sym, "ADS symbol resolved directly")
    except Exception as exc:
        log.warning("ADS connect: direct GVL_HA.xOnline lookup failed: %s", exc)
        online_sym = discover_symbol_prefix(p)
        symbol_cache["GVL_HA.xOnline"] = online_sym

    online = online_sym.read()
    log.info("ADS connected to %s / %s port %s, resolved xOnline=%s prefix='%s'",
             PLC_IP, PLC_AMS, ADS_PORT, online, symbol_prefix)
    discover_runtime_entities(p)


def pub_state(domain, legacy, value):
    mqttc.publish(topic_base(domain, legacy) + "/state", value, retain=True)


def poll_once():
    for e in ENT["lights"]:
        v = bool(read_symbol(e["state_symbol"]))
        pub_state("light", e["legacy_object_id"], "ON" if v else "OFF")
    for e in ENT["sensors"]:
        v = read_symbol(e["symbol"])
        pub_state("sensor", e["legacy_object_id"], f"{float(v):.1f}")
    for e in ENT["binary_sensors"]:
        v = bool(read_symbol(e["symbol"]))
        if e.get("invert"):
            v = not v
        pub_state("binary_sensor", e["legacy_object_id"], "ON" if v else "OFF")
    for e in ENT["switches"]:
        v = bool(read_symbol(e["state_symbol"]))
        pub_state("switch", e["legacy_object_id"], "ON" if v else "OFF")
    pub_state("binary_sensor", "gateway_online", "ON")
    mqttc.publish(f"{PREFIX}/availability", "online", retain=True)


def main():
    global mqttc, plc
    log.info("Starting Beckhoff TC3 Gateway TEST v0.2.3")
    log.info("Mode=%s, PLC=%s AMS=%s ADS=%s LocalAMS=%s",
             "TEST" if TEST else "PRODUCTION", PLC_IP, PLC_AMS, ADS_PORT, LOCAL_AMS)
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{DEVICE_ID}_gateway")
    if MQTT_USER:
        mqttc.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqttc.will_set(f"{PREFIX}/availability", "offline", retain=True)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(MQTT_HOST, MQTT_PORT, 60)
    mqttc.loop_start()

    while True:
        try:
            if plc is None or not plc.is_open:
                connect_ads()
            poll_once()
            time.sleep(POLL)
        except Exception as exc:
            log.warning("ADS/poll error: %s", exc)
            try:
                pub_state("binary_sensor", "gateway_online", "OFF")
                mqttc.publish(f"{PREFIX}/availability", "offline", retain=True)
            except Exception:
                pass
            try:
                if plc:
                    plc.close()
            except Exception:
                pass
            plc = None
            clear_symbol_cache()
            time.sleep(RECONNECT)


if __name__ == "__main__":
    main()
