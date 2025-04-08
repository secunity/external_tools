#!/usr/bin/env python3

import argparse
import subprocess
import time
# import socket
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import logging

# === Configuration ===
APP_LIST = ["ssh", "python3"]           # Predefined applications list for monitoring
CHECK_INTERVAL = 5                      # seconds
# FAILOVER_THRESHOLD = timedelta(minutes=5)
FAILOVER_THRESHOLD = 5 * 60             # Timeout 5 minutes

# === Logging Setup ===
logging.basicConfig(
    filename='./app_monitor.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# === Utility Functions ===

def is_process_running(process_name):
    try:
        subprocess.run(["pgrep", "-f", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def terminate_process(process_name):
    try:
        subprocess.run(["pkill", "-f", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def check_peer_reachable(ip):
    try:
        subprocess.run(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_application_status():
    peer_app_status = {app: "running" if is_process_running(app) else "not running" for app in APP_LIST}
    return all(peer_app_status.get(app) == 'running' for app in APP_LIST)

def get_peer_status(collection, peer_id):
    # return collection.find_one({"server_id": peer_id}, sort=[("timestamp", -1)])
    return collection.find_one({"server_id": peer_id})

# # The failover logic conditions
# def should_become_active(peer_doc, peer_reachable):
#     # print("should_become_active ENTER")
#     if not peer_doc:                                                                                # if no peer status
#         return True
#     # if peer_doc.get('applications') != "OK":                                                        # if peer application status is not OK
#     #     return True
    
#     # if ( all(peer_doc.get('applications')(app) == 'running' for app in APP_LIST) )
    
#     # Проверка, что все приложения из APP_LIST имеют статус 'running'
#     # print("======================")
#     # print("peer_doc: ", peer_doc)
#     # print("peer_doc.get('applications'): ", peer_doc.get('applications'))
#     # print("======================")
#     peer_app_status = peer_doc.get('applications')
#     peer_all_running = all(peer_app_status.get(app) == 'running' for app in APP_LIST)
#     # print("all_running: ", all_running)

#     if peer_all_running:
#         print("All peer apps is running.")                                                          # DEBUG
#         # return False
#     else:
#         print("Not all peer apps is running.")                                                      # DEBUG
#         return True
    
#     last_heartbeat = peer_doc.get("timestamp")
#     if not last_heartbeat:                                                                          # if there is no timestamp data
#         return True
#     age = int(time.time()) - last_heartbeat                                                         # if last peer time older than FAILOVER_THRESHOLD
#     return age > FAILOVER_THRESHOLD and not peer_reachable

def update_own_status(collection, server_id, mode, status):
    collection.update_one(
        {"server_id": server_id},
        {"$set": {
                "time": datetime.now(timezone.utc),                                                 # DEBUG
                "timestamp": int(time.time()),
                "mode": mode,
                "applications": status
                }
         },
        upsert=True
    )

def remote_timestamp_check(peer_doc):
    last_heartbeat = peer_doc.get("timestamp")
    if not last_heartbeat:                                                                          # if there is no timestamp data
        return False
    age = int(time.time()) - last_heartbeat                                                         # if last peer time older than FAILOVER_THRESHOLD
    print("time:")
    print('int(time.time()): ', int(time.time()))
    print('last_heartbeat: ', last_heartbeat)
    print("age: ", age)
    return age < FAILOVER_THRESHOLD

def remote_mode_check(peer_doc):
    print("remote_mode_check!!")
    return peer_doc.get("mode")

def get_peer_application_status(peer_doc):
    peer_app_status = peer_doc.get('applications')
    return all(peer_app_status.get(app) == 'running' for app in APP_LIST)

def switch_to_active():                                                                             # become active
    print("switch_to_active!")
    # mv /data/spectorious/work/attacks_rt/attacks_checker.py.orig /data/spectorious/work/attacks_rt/attacks_checker.py
    try:
        subprocess.run(["mv", "/data/spectorious/work/attacks_rt/attacks_checker.py.orig", 
                        "/data/spectorious/work/attacks_rt/attacks_checker.py"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logging.info("Successfully switch_to_active!")
        return True
    except subprocess.CalledProcessError:
        logging.info("Alert: can't switch_to_active!")
        return False

def alert_cant_switch_to_active():                                                                  # need to become active, but not all apps is OK
    print("alert_cant_switch_to_active!")
    return

def switch_to_passive():                                                                            # become passive
    print("switch_to_passive!")
    if terminate_process("attacks_checker.py"):
        try:
            subprocess.run(["mv", "/data/spectorious/work/attacks_rt/attacks_checker.py", 
                            "/data/spectorious/work/attacks_rt/attacks_checker.py.orig"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            logging.info("Successfully switch_to_passive!")
            return True
        except subprocess.CalledProcessError:
            logging.info("Alert: can't switch_to_passive!")
            return False
    else:
        logging.info("Alert: can't switch_to_passive!")
        return False
    # mv /data/spectorious/work/attacks_rt/attacks_checker.py /data/spectorious/work/attacks_rt/attacks_checker.py.orig 
    # root@ubu-torik:/data/spectorious/work/attacks_rt# ps -fe | grep attacks_checker.py
    # root        2966    2873  0 09:57 ?        00:00:05 python3 /data/spectorious/work/attacks_rt//attacks_checker.py

# === Main ===

def main():
    parser = argparse.ArgumentParser(description="Application Monitoring Script with Failover")
    parser.add_argument("--peer-ip", "-p", required=True)
    parser.add_argument("--local-ip", "-l", required=True)
    parser.add_argument("--mongo-uri", "-m", required=True)
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument("--mongo-collection", required=True)
    parser.add_argument("--mode", "-s", choices=["active", "passive"], help="Startup mode")
    args = parser.parse_args()

    server_id = args.local_ip
    peer_id = args.peer_ip

    client = MongoClient(args.mongo_uri)
    db = client[args.mongo_db]
    collection = db[args.mongo_collection]

    current_mode = args.mode or "passive"
    
    print("server_id: ", server_id)
    print("peer_id: ", peer_id)
    print("current_mode: ", current_mode)

    while True:
        try:
            # Determine peer state
            try:
                peer_reachable = check_peer_reachable(peer_id)                                      # ICMP reachebility
                # print("peer reachable status: ", peer_reachable)                                    # DEBUG
                peer_doc = get_peer_status(collection, peer_id)
                print("peer_doc: ", peer_doc)                                                       # DEBUG
            except Exception as e:
                logging.error(f"Error: {e}")
                timestamp_is_valid = False                                                          # no connectivity
                peer_apps_is_OK = False
            else:
                if peer_doc is None:                                                                # no data from peer
                    timestamp_is_valid = False
                    peer_apps_is_OK = False
                else:
                    
                    timestamp_is_valid = remote_timestamp_check(peer_doc)
                    peer_apps_is_OK = get_peer_application_status(peer_doc)
                    peer_mode = remote_mode_check(peer_doc)
                    print("прорвались!")
            
            # all rest conditions
            mode_CLI = args.mode or None
            peer_is_reachable = peer_reachable
            local_apps_is_OK = get_application_status()

            print("=========================")
            print("current_mode: ", current_mode)
            print("mode_CLI: ", mode_CLI)
            print("peer_is_reachable: ", peer_is_reachable)
            print("timestamp_is_valid: ", timestamp_is_valid)
            print("local_apps_is_OK: ", local_apps_is_OK)
            print("peer_apps_is_OK: ", peer_apps_is_OK)
            print("peer_mode: ", peer_mode)
            
            # main mpde seletion algorithm
            if mode_CLI != "active":
                if (not peer_is_reachable and not timestamp_is_valid and current_mode != "active"):
                    if local_apps_is_OK:
                        if switch_to_active():
                            current_mode = "active"
                    else:
                        alert_cant_switch_to_active()
                elif (current_mode == "passive" and peer_mode == "passive"):                        # возможно нужно исключить?
                    if local_apps_is_OK:
                        if switch_to_active():
                            current_mode = "active"
                    else:
                        alert_cant_switch_to_active()
                # failback (passive -> active-> passive)
                elif (current_mode == "active" and peer_mode == "active" and peer_is_reachable and timestamp_is_valid and peer_apps_is_OK):
                    if switch_to_passive():
                        current_mode = "passive"

            app_status = {app: "running" if is_process_running(app) else "not running" for app in APP_LIST}
            update_own_status(collection, server_id, current_mode, app_status)
            logging.info(f"Status updated: mode={current_mode}, apps={app_status}")

        except Exception as e:
            logging.error(f"Error: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
