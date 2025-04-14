# Application Monitoring and Failover Script
## Overview

This Python script monitors specified applications' statuses and manages failover between two servers. It ensures high availability by switching roles between active and passive modes based on application health and peer server status. The script uses MongoDB to store and retrieve the statuses of both servers, facilitating coordinated failover decisions.
## Usage

To execute the script, use the following command:

```
python3 app_monitor.py --peer-ip <PEER_IP> --local-ip <LOCAL_IP> --mongo-uri <MONGO_URI> --mongo-db <MONGO_DB> --mongo-collection <MONGO_COLLECTION> [--mode <MODE>]
```

### Parameters

- `--peer-ip (-p)`: IP address of the peer server.
- `--local-ip (-l)`: IP address of the local server.
- `--mongo-uri (-m)`: MongoDB connection URI.
- `--mongo-db`: Name of the MongoDB database.
- `--mongo-collection`: Name of the MongoDB collection.
- `--mode (-s)`: (Optional) Startup mode of the server. Choices are active or passive. If not specified, defaults to passive.

### Example

```
python3 app_monitor.py --peer-ip 192.168.1.2 --local-ip 192.168.1.1 --mongo-uri mongodb://user:password@localhost:27017/ --mongo-db app_status --mongo-collection statuses --mode active
```
In this example, the local server (192.168.1.1) starts in active mode, monitors the peer server at 192.168.1.2, and connects to the MongoDB instance at localhost:27017 using the specified credentials.
### Configuration

The script relies on a YAML configuration file named app_monitor.yaml for customizable settings:

app_list: List of applications to monitor (default: ["ssh", "python3"]).\
check_interval: Interval, in seconds, between health checks (default: 5 seconds).\
failover_threshold: Maximum time of not receiving a report from the peer, in seconds, to wait before initiating failover (default: 300 seconds).

### System Requirements

#### Python 3: Ensure Python 3 is installed on the system.
#### Required Python Packages:
- `argparse`: For parsing command-line arguments.
- `subprocess`: For executing system commands.
- `time`, datetime, logging: Standard libraries for time tracking and logging.
- `yaml`: For reading the YAML configuration file. Install with pip install pyyaml.
- `pymongo`: For MongoDB interactions. Install with pip install pymongo.

To install all the necessary Python modules, run `pip install pymongo pyyaml`.

#### MongoDB: 
Access to a MongoDB instance to store server statuses. MongoDB version 4.4.29 and above were tested.

#### System Utilities:

- `pgrep`: To check if a process is running.
- `pkill`: To terminate processes.
- `ping`: To check peer server reachability.

### Notes

The script manages failover by monitoring application statuses and peer server health. \
If the active server detects issues with its applications or loses contact with the peer, it can switch roles to passive if the role is not explicitly set to active from the CLI.\
The local server in the passive mode can be switched to the active mode in the next cases:
- If current mode is passive and detects the peer is unreachable AND peer’s MongoDB heartbeat is older than "failover_threshold" (5 minutes by default).
- If current mode is passive and remote peer mode is also passive and current node is OK.\

The server can switch back to passive mode if the peer is reachable, peer application status is OK and the last report from the peer was generated not later than ‘failover_threshold’. 

Ensure the MongoDB instance is accessible and the provided credentials have the necessary permissions to read and write to the specified database and collection.

The script logs its operations to app_monitor.log, which can be reviewed for troubleshooting and auditing purposes.

## Author

Denis Chertkov\
denis\@chertkov.info\
version 1.05\
Date: [2025-04-14]
