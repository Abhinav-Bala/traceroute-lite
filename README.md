## Traceroute Clone

I'm currently taking a Computer Networks class and was reading a section about the ICMP (Internet Control Message Protocol). It discussed how the tool `traceroute` leverages some of the features of the protocol to effectively map out each hop a packet takes to reach its destination.

It's built off the fact that if a packet's TTL (Time To Live) expires en-route to the destination, the router will send an ICMP "Time Exceeded" packet back to the source. This packet will contain the source ip which is used to keep track of each router that our packet passes through. By incrementing the TTL from 1 until we reach the destination, we can map out each hop along the path. 

Another cool part is that traceroute sets the destination port to something that's very unlikely to be used (32456 for example). This ensures that when we finally reach the destination, it will send a "Port Unreachable" ICMP error back, signalling that we've successfully reached the destination without affecting any live ports or services.

## How to Use

### Requirements

- Python 3.11 > 
- Root/admin privileges, we need raw sockets to be able to receive ICMP packets

### Basic Usage

Run with sudo/admin privileges:

```bash
sudo python3 traceroute.py
```

This will trace the route to the default destination (`abhinavbala.com`).

### Command Line Arguments

- `--destination`: The hostname or IP address to trace (default: `abhinavbala.com`)
- `--max_ttl`: Maximum TTL value before terminating (default: `64`)
- `--port`: Destination port to use for UDP packets (default: `32456`)
- `--packet_size`: Size of the packet in bytes to send (default: `40`)

### Examples

Trace to Google:
```bash
sudo python3 traceroute.py --destination google.com
```

Trace with a larger packet size:
```bash
sudo python3 traceroute.py --destination example.com --packet_size 100
```

### Output Format

The output shows:
- TTL (hop number)
- Round-trip time for each of the 3 probes (in milliseconds)
- Source IP address of each router

Example output:
```
Tracing route to google.com with ip address 142.250.184.174 with packet size 40
TTL (1): 10.5 ms  12.3 ms  11.8 ms  192.168.1.1
TTL (2): 15.2 ms  10.4 ms  14.9 ms  10.0.3.192
TTL (3): 20.1 ms  19.8 ms  20.3 ms  172.16.7.33
...
TTL (7): 25.1 ms  24.8 ms  25.3 ms  74.125.119.226 (destination reached!)
Done tracing
```



