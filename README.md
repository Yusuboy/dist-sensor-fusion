# Distributed Sensor Fusion System

## 📌 Overview
This project implements a **distributed sensor-fusion system** where multiple nodes act as sensor gateways.  
Each node:
- Generates a local sensor reading (e.g., temperature).
- Shares its reading with other nodes via TCP sockets and JSON messages.
- Maintains a **shared global state** containing the latest readings from all nodes.
- Participates in **leader election** and **checkpoint agreement** to ensure consensus.

The prototype runs on **three nodes**, but the design scales to many nodes worldwide.

---

## 🎯 Goals
The project demonstrates key distributed systems concepts:
1. **Shared state** – Each node stores sensor values for all nodes.  
2. **Consistency** – Nodes exchange updates to converge on the same global state.  
3. **Consensus** – Nodes elect a leader and agree on checkpoints of the global state.  
4. **Fault tolerance** – Leader failure triggers re-election.  
5. **Scalability** – Design supports gossip protocols and hierarchical leaders for large deployments.

---

## 🏗️ Architecture
- **Nodes:** Identical software, each can become leader.  
- **Leader:** Sends heartbeats, proposes checkpoints, collects acknowledgements.  
- **Messages:**  
  - `SENSOR_UPDATE` – Share local reading  
  - `STATE_UPDATE` – Exchange global state  
  - `HEARTBEAT` – Leader liveness  
  - `ELECTION_REQUEST / ELECTION_VOTE` – Leader election  
  - `CHECKPOINT_PROPOSE / CHECKPOINT_ACK` – Consensus on state snapshot  

---

## 🔄 Sequence Diagrams
### Leader Election
1. Node times out without heartbeat.  
2. Sends `ELECTION_REQUEST` to peers.  
3. Majority votes → becomes leader.  
4. Leader sends `HEARTBEAT` to followers.  

### Checkpoint Agreement
1. Leader proposes checkpoint with global state.  
2. Followers reply with `CHECKPOINT_ACK`.  
3. Majority ACK → checkpoint committed.  

### State Dissemination
- Nodes periodically exchange `SENSOR_UPDATE` and `STATE_UPDATE`.  
- Merge rule: **last-writer-wins** using timestamps.  
- Anti-entropy exchanges repair missed updates.

---