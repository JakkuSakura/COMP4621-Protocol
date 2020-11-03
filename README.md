# COMP4621-Protocol
An application-level reliable network protocol upon UDP, a final project of COMP4721

## Protocol
### Data Types
`int` 4 bytes
`data` 4 + n bytes

### Packets
ACK
```
int 0x01
int confirmed_id
```

CLOSE
```
int 0x02
```

DATA
```
int 0x03
int packet_id
data actual data
```

WINDOW
```
int 0x04
int window_size
```

### Handshaking process
client sends an `WINDOW` Packet to server, server sends back an `ACK` and a suitable `WINDOW` and client sends an `ACK`, handshaking finishes
 
