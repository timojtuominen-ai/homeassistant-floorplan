from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
    "import json, logging, os, socket, threading, time",
    "import glob, json, logging, os, shutil, socket, subprocess, threading, time\nfrom datetime import datetime, timezone",
)
s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.31"',
    '"sw_version":"Kotiautomaatio_TC3 v0.32.1"',
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.3 commissioning + heating controls",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.6 service diagnostics",
)
s = s.replace(
    "plc=None; mqttc=None; ads_lock=threading.Lock(); symbol_cache={}; command_map={}; last_sensor_publish=0.0; SENSOR_INTERVAL=30.0",
    "plc=None; mqttc=None; ads_lock=threading.Lock(); symbol_cache={}; command_map={}; last_sensor_publish=0.0; SENSOR_INTERVAL=30.0; plc_run_started_monotonic=None; plc_last_restart_iso=None",
)

insert = r'''

# v1.0.6: Service page sources from Kotiautomaatio_TC3 v0.32.1.
EXTRA_SENSORS_V106 = [
    {"legacy_object_id":"lattialammitys_meno_lampotila","name":"Lattialämmitys meno lämpötila","symbol":"GVL_HA.rTemperature_11_Lattialammitys_meno_lampotila","unit":"°C","device_class":"temperature"},
    {"legacy_object_id":"lattialammitys_paluu_lampotila","name":"Lattialämmitys paluu lämpötila","symbol":"GVL_HA.rTemperature_12_Lattialammitys_paluu_lampotila","unit":"°C","device_class":"temperature"},
]
for _e in EXTRA_SENSORS_V106:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["sensors"]):
        ENT["sensors"].append(_e)

EXTRA_BINARY_V106 = [
    {"legacy_object_id":"pumppaamo_vika","name":"Pumppaamo vika","symbol":"GVL_HA.xAlarm_WastePumpFault","device_class":"problem","invert":False},
    {"legacy_object_id":"akkulaturi_vika","name":"Akkulaturi vika","symbol":"GVL_HA.xAlarm_BatteryChargerFault","device_class":"problem","invert":False},
    {"legacy_object_id":"lattialammitys_paine_matala","name":"Lattialämmityspiirin paine matala","symbol":"GVL_HA.xAlarm_FloorHeatingPressure","device_class":"problem","invert":False},
]
for _e in EXTRA_BINARY_V106:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)

DIAGNOSTIC_BINARY_V106 = [
    {"id":"beckhoff_cx9240_gateway_kaynnissa","name":"Beckhoff CX9240 gateway käynnissä","device_class":"connectivity"},
    {"id":"plc_yhteys","name":"PLC-yhteys","device_class":"connectivity"},
    {"id":"ads_gateway_yhteys","name":"ADS-gateway-yhteys","device_class":"connectivity"},
    {"id":"raspberry_pi_throttled","name":"Raspberry Pi alijännite tai throttling","device_class":"problem"},
]
DIAGNOSTIC_SENSORS_V106 = [
    {"id":"twincat_runtime_state","name":"TwinCAT Runtime","icon":"mdi:state-machine"},
    {"id":"plc_uptime","name":"PLC-yhteyden käyntiaika","unit":"s","device_class":"duration","state_class":"measurement"},
    {"id":"plc_last_restart","name":"Viimeisin havaittu PLC-käynnistys","device_class":"timestamp"},
    {"id":"ads_last_success","name":"ADS viimeksi yhteydessä","device_class":"timestamp"},
    {"id":"raspberry_pi_uptime","name":"Raspberry Pi käyntiaika","unit":"s","device_class":"duration","state_class":"measurement"},
    {"id":"raspberry_pi_cpu_temperature","name":"Raspberry Pi CPU-lämpötila","unit":"°C","device_class":"temperature","state_class":"measurement"},
    {"id":"raspberry_pi_disk_free","name":"Raspberry Pi levytilaa jäljellä","unit":"GB","device_class":"data_size","state_class":"measurement"},
    {"id":"raspberry_pi_memory_usage","name":"Raspberry Pi muistin käyttö","unit":"%","state_class":"measurement","icon":"mdi:memory"},
]

def diagnostic_topics(domain, oid):
    return (
        f"homeassistant/{domain}/beckhoff_cx9240/{oid}/config",
        f"beckhoff_cx9240/diagnostic/{oid}/state",
    )

def publish_diagnostic_configs():
    for e in DIAGNOSTIC_BINARY_V106:
        disc,state=diagnostic_topics("binary_sensor",e["id"])
        cfg={"name":e["name"],"unique_id":f"beckhoff_cx9240_{e['id']}","default_entity_id":f"binary_sensor.{e['id']}","state_topic":state,"availability_topic":"beckhoff_cx9240/availability","payload_available":"online","payload_not_available":"offline","payload_on":"ON","payload_off":"OFF","device_class":e["device_class"],"device":device()}
        mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True)
    for e in DIAGNOSTIC_SENSORS_V106:
        disc,state=diagnostic_topics("sensor",e["id"])
        cfg={"name":e["name"],"unique_id":f"beckhoff_cx9240_{e['id']}","default_entity_id":f"sensor.{e['id']}","state_topic":state,"availability_topic":"beckhoff_cx9240/availability","payload_available":"online","payload_not_available":"offline","device":device()}
        for key in ("unit","device_class","state_class","icon"):
            if e.get(key) is not None:
                cfg[{"unit":"unit_of_measurement"}.get(key,key)]=e[key]
        mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True)

def pub_diag(oid, value):
    pub(f"beckhoff_cx9240/diagnostic/{oid}/state",value)

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

ADS_STATE_NAMES = {
    0:"INVALID",1:"IDLE",2:"RESET",3:"INIT",4:"START",5:"RUN",6:"STOP",
    7:"SAVECFG",8:"LOADCFG",9:"POWERFAILURE",10:"POWERGOOD",11:"ERROR",
    12:"SHUTDOWN",13:"SUSPEND",14:"RESUME",15:"CONFIG",16:"RECONFIG",17:"STOPPING",
}

def runtime_state():
    with ads_lock:
        state=plc.read_state()
    ads_state=state[0] if isinstance(state,(tuple,list)) else state
    try:
        ads_state=int(ads_state)
    except Exception:
        pass
    return ADS_STATE_NAMES.get(ads_state,str(ads_state))

def raspberry_pi_uptime():
    try:
        return int(float(Path("/proc/uptime").read_text().split()[0]))
    except Exception:
        return None

def raspberry_pi_cpu_temperature():
    candidates=[]
    for type_path in glob.glob("/sys/class/thermal/thermal_zone*/type"):
        try:
            kind=Path(type_path).read_text().strip().lower()
            temp_path=Path(type_path).with_name("temp")
            value=float(temp_path.read_text().strip())
            if value > 1000:
                value/=1000.0
            candidates.append((0 if kind in ("cpu-thermal","soc_thermal","cpu_thermal") else 1,value))
        except Exception:
            continue
    if not candidates:
        return None
    return round(sorted(candidates)[0][1],1)

def raspberry_pi_memory_usage():
    try:
        values={}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key,value=line.split(":",1)
            values[key]=float(value.strip().split()[0])
        total=values["MemTotal"]
        available=values.get("MemAvailable",values.get("MemFree",0.0))
        return round((total-available)*100.0/total,1)
    except Exception:
        return None

def raspberry_pi_disk_free():
    try:
        return round(shutil.disk_usage("/data").free/(1024.0**3),1)
    except Exception:
        return None

def raspberry_pi_throttled():
    try:
        result=subprocess.run(["vcgencmd","get_throttled"],capture_output=True,text=True,timeout=2,check=True)
        raw=result.stdout.strip().split("=")[-1]
        return int(raw,16) != 0
    except Exception:
        pass
    for alarm_path in glob.glob("/sys/class/hwmon/hwmon*/in0_lcrit_alarm"):
        try:
            name_path=Path(alarm_path).with_name("name")
            name=name_path.read_text().strip().lower() if name_path.exists() else ""
            if "rpi" in name or "volt" in name:
                return Path(alarm_path).read_text().strip() == "1"
        except Exception:
            continue
    return None
'''

s = s.replace("\ndef setup_discovery():", insert + "\n\ndef setup_discovery():")
s = s.replace(
    '    for e in NUMBERS: publish_number_config(e)\n    publish_room_configs();',
    '    for e in NUMBERS: publish_number_config(e)\n    publish_diagnostic_configs()\n    publish_room_configs();',
)
s = s.replace(
    "def connect_ads():\n    global plc",
    "def connect_ads():\n    global plc,plc_run_started_monotonic,plc_last_restart_iso",
)
s = s.replace(
    'plc=p; symbol_cache.clear(); online=read("GVL_HA.xOnline"); log.info("ADS connected to %s / %s port %s, xOnline=%s",PLC_IP,PLC_AMS,ADS_PORT,online)',
    'plc=p; symbol_cache.clear(); online=read("GVL_HA.xOnline"); plc_run_started_monotonic=time.monotonic(); plc_last_restart_iso=utc_now_iso(); pub_diag("plc_yhteys","ON"); pub_diag("ads_gateway_yhteys","ON"); pub_diag("plc_last_restart",plc_last_restart_iso); log.info("ADS connected to %s / %s port %s, xOnline=%s",PLC_IP,PLC_AMS,ADS_PORT,online)',
)
s = s.replace(
    '    pub("beckhoff_cx9240/availability","online")\ndef main():',
    '''    now_iso=utc_now_iso()
    pub_diag("beckhoff_cx9240_gateway_kaynnissa","ON")
    pub_diag("plc_yhteys","ON")
    pub_diag("ads_gateway_yhteys","ON")
    pub_diag("twincat_runtime_state",runtime_state())
    pub_diag("ads_last_success",now_iso)
    if plc_run_started_monotonic is not None:
        pub_diag("plc_uptime",str(max(0,int(time.monotonic()-plc_run_started_monotonic))))
    if plc_last_restart_iso is not None:
        pub_diag("plc_last_restart",plc_last_restart_iso)
    if publish_sensors:
        pi_uptime=raspberry_pi_uptime()
        pi_temp=raspberry_pi_cpu_temperature()
        pi_memory=raspberry_pi_memory_usage()
        pi_disk=raspberry_pi_disk_free()
        pi_throttled=raspberry_pi_throttled()
        if pi_uptime is not None: pub_diag("raspberry_pi_uptime",str(pi_uptime))
        if pi_temp is not None: pub_diag("raspberry_pi_cpu_temperature",f"{pi_temp:.1f}")
        if pi_memory is not None: pub_diag("raspberry_pi_memory_usage",f"{pi_memory:.1f}")
        if pi_disk is not None: pub_diag("raspberry_pi_disk_free",f"{pi_disk:.1f}")
        if pi_throttled is not None: pub_diag("raspberry_pi_throttled","ON" if pi_throttled else "OFF")
    pub("beckhoff_cx9240/availability","online")
def main():''',
)
s = s.replace(
    "    global mqttc,plc",
    "    global mqttc,plc,plc_run_started_monotonic",
)
s = s.replace(
    '            log.warning("ADS/poll error: %s",exc)\n            try:',
    '            log.warning("ADS/poll error: %s",exc)\n            pub("beckhoff_cx9240/availability","online"); pub_diag("beckhoff_cx9240_gateway_kaynnissa","ON"); pub_diag("plc_yhteys","OFF"); pub_diag("ads_gateway_yhteys","OFF"); pub_diag("twincat_runtime_state","UNKNOWN"); plc_run_started_monotonic=None\n            try:',
)

p.write_text(s,encoding="utf-8")
print("patched gateway main.py for v1.0.6")

