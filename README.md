# Distributed Sensor Fusion System

## 📌 Overview
This project implements a **distributed sensor-fusion system** where multiple nodes act as sensor gateways.  
Each node:

- Generates a local sensor reading (e.g., temperature).
- Exchanges readings with other nodes using TCP sockets and JSON messages.
- Maintains a **shared global state** containing the latest readings from all nodes.
- Participates in a **Raft-style leader election** to coordinate updates.
- Detects leader failure and triggers re-election when needed.

The system runs with **three nodes**, but the architecture can be extended to more.

---

## 🎯 Goals
This project demonstrates core distributed systems concepts:

1. **Shared state** – Nodes fuse and propagate timestamped sensor readings.  
2. **Consistency** – Followers update their global state using leader heartbeats.  
3. **Consensus** – Nodes elect a leader using a majority-based voting mechanism.  
4. **Fault tolerance** – Killing the leader triggers a new election automatically.  
5. **Scalability** – More nodes can be added by extending peer lists.

---

## 🏗️ Architecture
- **Nodes**: All run identical logic and can become leader.  
- **Leader**: Sends regular heartbeats containing the fused global state.  
- **Followers**: Update their state and reset election timers on each heartbeat.  

### Message types implemented:
- `REQUEST_VOTE` – Candidate asks peers to grant a vote  
- `VOTE_RESPONSE` – Peer grants or denies a vote  
- `HEARTBEAT` – Leader liveness + state update  
- `SENSOR_UPDATE` – Local sensor reading sent to peers  
- `HELLO / HELLO_ACK` – Handshake barrier to prevent early elections  

These match the actual project functionality.

---

## 🔄 Sequence Diagrams
### Leader Election
1. A follower does not receive heartbeats → election timeout.  
2. It becomes a candidate and sends `REQUEST_VOTE` to peers.  
3. Peers respond with `VOTE_RESPONSE`.  
4. If a majority is reached → the candidate becomes leader.  
5. The leader begins sending heartbeats.

### State Dissemination
- Each node periodically updates its sensor value.  
- Nodes merge incoming updates using **last-writer-wins** timestamps.  
- The leader distributes the fused state through heartbeats.  

This ensures **eventual consistency** across the cluster.

---

## 🚨 Fault Tolerance
The system supports leader failure detection:

- If heartbeats stop arriving, followers trigger a new election.  
- A new leader is chosen automatically.  
- The dashboard marks nodes as offline when killed.  

This process is visible during the demo.


## ▶️ How to Run

### 1. Clone the repository
```bash
git clone https://github.com/Yusuboy/dist-sensor-fusion

cd dist-sensor-fusion
```

 ### 2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate

```

 ### 3. Start the full cluster with dashboard
```bash
python3 -m scripts.run_cluster

``` 

 ### 4. Kill a node (in another terminal)
 You can kill **any** node by specifying its ID (`A`, `B`, or `C`):
```bash
python3 scripts/kill_node.py A
```