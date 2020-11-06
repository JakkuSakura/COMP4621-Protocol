# COMP4621-Protocol
An application-level reliable network protocol upon UDP, a final project of COMP4721
## Functionalities
- Reliable data transfer(both sender side and receiver side): resistant to disordering, packet loss and corruption.
- Batch ACK
- Basic timeout and retransmit
- 0RTT Handshaking

## Protocol
### Data Types
`int` 4 bytes, big endian
`data` 4 + n bytes, first 4 byte is its pure data length

### Packets
Packet
```
int seq_num
int ack_num
int chk_sum
data payload
```
 
## Architecture
- adaptors.py: interface `Socket` and its implementations like `DebugSocket`(prints received and sent data), `DropoutSocket`(drops packets randomly), `CorruptedSocket`(shuffles individual packets probabilistically), `ArraySocket`(for manually construct packets), `DisorderSocket`(shuffle packets probabilistically), and **`UdtAdaptor`(utilizes udt.py here)**
- tools.py: some tools, including `ByteBuf` and `print_info`(print with mutex for testing)
- packet.py: packet format
- protocol.py: core code is implemented here. It should be rdt.py but I finished it before rdt.py template was released. I am too lazy to rename it.
- receiver.py
- sender.py
- udt.py

