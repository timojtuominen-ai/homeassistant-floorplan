from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

# The former production/test gateway used the MQTT Discovery device identifier
# "beckhoff_cx5000". Its retained config messages survive removal of the old
# add-on and make Home Assistant recreate a second Beckhoff CX9240 device.
# Subscribe to that exact obsolete namespace and delete every retained config
# received from it. The active production namespace is "beckhoff_ads", so the
# working entities and their entity IDs are not touched.
setup_marker = '''def setup_discovery():
    if not DISCOVERY:return
    command_map.clear()'''
setup_replacement = '''def setup_discovery():
    if not DISCOVERY:return
    mqttc.subscribe("homeassistant/+/beckhoff_cx5000/+/config")
    log.info("MQTT discovery cleanup armed for obsolete beckhoff_cx5000 device")
    command_map.clear()'''
if setup_marker not in s:
    raise RuntimeError("v1.0.15 setup_discovery insertion point was not found")
s = s.replace(setup_marker, setup_replacement, 1)

message_marker = "def on_message(client,userdata,msg):\n"
message_replacement = '''def on_message(client,userdata,msg):
    if (msg.topic.startswith("homeassistant/")
            and "/beckhoff_cx5000/" in msg.topic
            and msg.topic.endswith("/config")):
        if msg.payload:
            mqttc.publish(msg.topic, b"", retain=True)
            log.info("MQTT discovery cleanup removed obsolete config: %s", msg.topic)
        return
'''
if message_marker not in s:
    raise RuntimeError("v1.0.15 on_message insertion point was not found")
s = s.replace(message_marker, message_replacement, 1)

s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.14 lighting groups and cleaning modes",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.15 obsolete MQTT discovery cleanup",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.15")
