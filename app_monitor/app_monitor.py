#!/usr/bin/env python3
#######################################################################################################
# Application Monitoring and Failover Script.
# This Python script monitors specified applications' statuses and manages failover between two servers.
# It ensures high availability by switching roles between active and passive modes based on application
# health and peer server status. The script uses MongoDB to store and retrieve the statuses of both servers,
# facilitating coordinated failover decisions..
#
# Usage:
#   python3 app_monitor.py --peer-ip <PEER_IP> --local-ip <LOCAL_IP> --mongo-uri <MONGO_URI>
#                          --mongo-db <MONGO_DB> --mongo-collection <MONGO_COLLECTION> [--mode <MODE>]
#
# See the README file for the details
#
# # Default values:
# app_list: List of applications to monitor (default: ["ssh", "python3"]).
# check_interval: Interval, in seconds, between health checks (default: 5 seconds).
# failover_threshold: Time, in seconds, to wait before initiating failover (default: 300 seconds).
#
# Example:
#   python3 app_monitor.py --peer-ip 1.1.1.1 --mongo-uri 172.20.1.62 --mongo-db SeriesDB \
#     --mongo-collection series -l 127.0.0.1
#
# Requirements:
# Required Python Packages:
#   argparse: For parsing command-line arguments.
#   subprocess: For executing system commands.
#   time, datetime, logging: Standard libraries for time tracking and logging.
#   yaml: For reading the YAML configuration file. Install with pip install pyyaml.
#   pymongo: For MongoDB interactions. Install with pip install pymongo.
# MongoDB version 4.4.29 or newer.
# System Utilities:
#   pgrep
#   pkill
#   ping
#
# Author: Denis Chertkov, denis@chertkov.info
# version 1.05
# Date: [2025-04-14]
#######################################################################################################

import argparse
import subprocess
import time
from datetime import datetime, timezone
import yaml
from pymongo import MongoClient
import logging

# === Default configuration and constants ===
DEFAULT_APP_LIST = ["ssh", "python3"]           # Predefined applications list for monitoring
DEFAULT_CHECK_INTERVAL = 5                      # seconds
DEFAULT_FAILOVER_THRESHOLD = 5 * 60             # Timeout 5 minutes
CONFIG_FILE_NAME = "app_monitor.yaml"           # Config file name
LOG_FILE_NAME= "app_monitor.log"                # Log file name
APP_LIST = []
CHECK_INTERVAL = 30
FAILOVER_THRESHOLD = 5 * 60

# === Logging Setup ===
logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)


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
    try:
        doc = collection.find_one({"server_id": peer_id})
        return doc
    except Exception as e:
        logging.error(f"{e}")
        logging.error("Cooud not fetch the data from the MongoDB")
        return None


def update_own_status(collection, server_id, mode, status):
    try:
        collection.update_one(
            {"server_id": server_id},
            {"$set": {
                    "time": datetime.now(timezone.utc),                                             # DEBUG, can be deleted
                    "timestamp": int(time.time()),
                    "mode": mode,
                    "applications": status
                    }
            },
            upsert=True
        )
    except Exception as e:
        logging.error(f"{e}")
        logging.error("Cooud not update the data on the MongoDB")


def remote_timestamp_check(peer_doc, delta):
    last_heartbeat = peer_doc.get("timestamp")
    if not last_heartbeat:                                                                          # if there is no timestamp data
        return False
    age = int(time.time()) - last_heartbeat                                                         # if last peer time older than FAILOVER_THRESHOLD
    # print("time:")
    # print('int(time.time()): ', int(time.time()))
    # print('last_heartbeat: ', last_heartbeat)
    # print("age: ", age)
    return age < delta


def remote_mode_check(peer_doc):
    return peer_doc.get("mode")


def get_peer_application_status(peer_doc):
    peer_app_status = peer_doc.get('applications')
    return all(peer_app_status.get(app) == 'running' for app in APP_LIST)


def switch_to_active():                                                                             # become active
    logging.info("Trying to switch to active mode!")
    # mv /data/spectorious/work/attacks_rt/attacks_checker.py.orig /data/spectorious/work/attacks_rt/attacks_checker.py
    try:
        subprocess.run(["mv", "/data/spectorious/work/attacks_rt/attacks_checker.py.orig", 
                        "/data/spectorious/work/attacks_rt/attacks_checker.py"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logging.info("Successfully switched to active mode!")
        return True
    except subprocess.CalledProcessError:
        alert_cant_switch_to_active()
        return False


def alert_cant_switch_to_active():                                                                  # need to become active, but not all apps is OK
    logging.info("Alert: can't switch to active mode!")
    return


def alert_cant_switch_to_passive():                                                                 # need to become passive, but can't
    logging.info("Alert: can't switch to passive mode!")
    return


def switch_to_passive():                                                                            # become passive
    logging.info("Trying to switch to passive mnode!")
    reply = subprocess.run(["mv", "/data/spectorious/work/attacks_rt/attacks_checker.py",
                            "/data/spectorious/work/attacks_rt/attacks_checker.py.orig"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)                   # without exeption raising: ", check=True"
    if reply.returncode == 0:
        if terminate_process("attacks_checker.py"):
            logging.info("Successfully switched to the passive mode!")
            return True
        else:
            alert_cant_switch_to_passive()
            return False
    else:
        alert_cant_switch_to_passive()
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
    mode_CLI = args.mode or None

    # read the configuration from yaml file
    try:
        with open(CONFIG_FILE_NAME, 'r') as config_file:
            config = yaml.full_load(config_file)
        APP_LIST = config.get('app_list', DEFAULT_APP_LIST)                                             # Predefined applications list
        CHECK_INTERVAL = config.get('check_interval', DEFAULT_CHECK_INTERVAL)                           # seconds
        FAILOVER_THRESHOLD = config.get('failover_threshold', DEFAULT_FAILOVER_THRESHOLD)               # Timeout 5 minutes
    except Exception as e:
        logging.error(f"{e}")
        logging.error("The config file has not been loaded, Abnormal program termination.")
        print("The config file has not been loaded, Abnormal program termination.")
        exit(127)

    logging.info("The program is started")
    logging.info("Current status is: server_id=%s, peer_id=%s, current_mode=%s, app_list=%s, check_interval=%s, failover_threshold=%s",
                 server_id, peer_id, current_mode, APP_LIST, CHECK_INTERVAL, FAILOVER_THRESHOLD)

    print("======== Current status ==========")
    print("server_id:", server_id)
    print("peer_id:", peer_id)
    print("current_mode:", current_mode)
    print("app_list:", APP_LIST)
    print("check_interval:", CHECK_INTERVAL)
    print("failover_threshold:", FAILOVER_THRESHOLD)
    print("==================================")

    while True:
        try:
            # Determine peer state
            try:
                peer_reachable = check_peer_reachable(peer_id)                                      # ICMP reachebility
                peer_doc = get_peer_status(collection, peer_id)
                # print("peer_doc: ", peer_doc)                                                       # DEBUG
            except Exception as e:
                logging.error(f"Error: {e}")
                timestamp_is_valid = False                                                          # no connectivity
                peer_apps_is_OK = False
                peer_mode = "passive"
            else:
                if peer_doc is None:                                                                # no data from peer
                    timestamp_is_valid = False
                    peer_apps_is_OK = False
                    peer_mode = "passive"
                else:

                    timestamp_is_valid = remote_timestamp_check(peer_doc, FAILOVER_THRESHOLD)
                    peer_apps_is_OK = get_peer_application_status(peer_doc)
                    peer_mode = remote_mode_check(peer_doc)

            # all rest conditions
            peer_is_reachable = peer_reachable
            local_apps_is_OK = get_application_status()

            # main mode seletion algorithm
            if mode_CLI != "active":
                if (not peer_is_reachable and not timestamp_is_valid and current_mode != "active"):
                    if local_apps_is_OK:
                        if switch_to_active():
                            current_mode = "active"
                    else:
                        alert_cant_switch_to_active()
                elif (current_mode == "passive" and peer_mode == "passive"):                        # if both nodes is passive switch to active
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
        except Exception as e:
            logging.error(f"Error2: {e}")
        finally:
            # log the detailed status of the local and remote nodes
            logging.info(
                "Status updated: mode=%s, apps=%s, mode_cli=%s, peer_is_reachable=%s, timestamp_is_valid=%s, "
                "local_apps_is_ok=%s, peer_apps_is_ok=%s, peer_mode=%s",
                current_mode, app_status, mode_CLI, peer_is_reachable, timestamp_is_valid,
                local_apps_is_OK, peer_apps_is_OK, peer_mode
            )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
