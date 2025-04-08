#!/usr/bin/env python3

import argparse
import subprocess
import time
import socket
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

def check_peer_reachable(ip):
    try:
        subprocess.run(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_application_status():
    return {app: "running" if is_process_running(app) else "not running" for app in APP_LIST}

def get_peer_status(collection, peer_id):
    # return collection.find_one({"server_id": peer_id}, sort=[("timestamp", -1)])
    return collection.find_one({"server_id": peer_id})

# The failover logic conditions
def should_become_active(peer_doc, peer_reachable):
    # print("should_become_active ENTER")
    if not peer_doc:                                                                                # if no peer status
        return True
    # if peer_doc.get('applications') != "OK":                                                        # if peer application status is not OK
    #     return True
    
    # if ( all(peer_doc.get('applications')(app) == 'running' for app in APP_LIST) )
    
    # Проверка, что все приложения из APP_LIST имеют статус 'running'
    # print("======================")
    # print("peer_doc: ", peer_doc)
    # print("peer_doc.get('applications'): ", peer_doc.get('applications'))
    # print("======================")
    peer_app_status = peer_doc.get('applications')
    peer_all_running = all(peer_app_status.get(app) == 'running' for app in APP_LIST)
    # print("all_running: ", all_running)

    if peer_all_running:
        print("All peer apps is running.")                                                          # DEBUG
        # return False
    else:
        print("Not all peer apps is running.")                                                      # DEBUG
        return True
    
    last_heartbeat = peer_doc.get("timestamp")
    if not last_heartbeat:                                                                          # if there is no timestamp data
        return True
    age = int(time.time()) - last_heartbeat                                                         # if last peer time older than FAILOVER_THRESHOLD
    return age > FAILOVER_THRESHOLD and not peer_reachable

def update_own_status(collection, server_id, mode, status):
    collection.update_one(
        {"server_id": server_id},
        {"$set": {
                "time": datetime.now(timezone.utc),
                "timestamp": int(time.time()),
                "mode": mode,
                "applications": status
                }
         },
        upsert=True
    )

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

    # server_id = socket.gethostname()
    # peer_id = "node2" if server_id == "node1" else "node1"
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
            peer_doc = get_peer_status(collection, peer_id)
            print("peer_doc: ", peer_doc)                                                           # DEBUG
            peer_reachable = check_peer_reachable(peer_id)                                          # ICMP reachebility
            print("peer reacheble status: ", peer_reachable)                                        # DEBUG

            # If no fixed mode passed, calculate mode
            if not args.mode:
                if current_mode == "passive" and should_become_active(peer_doc, peer_reachable):
                    logging.info("Switching to ACTIVE mode due to peer failure.")
                    current_mode = "active"
                    # TODO - active mode starting procedure
                elif current_mode == "active" and peer_doc and peer_reachable:
                    # Optional: add logic to fall back to passive if peer recovers
                    pass

            # # Monitor applications
            app_status = get_application_status()
            print("app_status: ", app_status)                                                       # DEBUG

            # # In active mode, add peer monitoring (can be simulated or real via SSH, etc.)
            # if current_mode == "active":
            #     peer_apps = {f"{app}_peer": "assumed down" for app in APP_LIST}
            #     app_status.update(peer_apps)
            
            update_own_status(collection, server_id, current_mode, app_status)
            logging.info(f"Status updated: mode={current_mode}, apps={app_status}")

        except Exception as e:
            logging.error(f"Error: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
