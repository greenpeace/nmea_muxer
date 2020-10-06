### NMEA MULTIPLEXER

**NMEA feed multiplexer and controller software written in Python**

This project aims to create a user friendly way to route NMEA sentences to various networks with configurable combinations.

It also helps to remove clutter from serial servers, by enabling a higher number of clients to connect.

—
**Hint**
The maximum number of socket connections is defined in Linux systems under the file `/proc/sys/net/core/somaxconn`.
—

###### Features
-Managing multiple listeners (socket connections to serial inputs) and talkers (sockets that handle clients and emit their feeds)
-Filtering sentences
-Throttling feeds, either cumulative (FIFO, e.g. for AIS messages) or by sending only the latest batch (LIFO/FINO, e.g. for GPS) to the specified network
-Ordering of listeners and their sentences in throttle mode
-Resilience settings for listeners and the whole app, where it automatically restarts the socket or application depending on potential problems
-Feed preview and clients list for talkers, application log feed
-Storing and loading settings

#### Managing Listeners
Listeners are the input mechanism for the multiplexer. They create asynchronious TCP sockets to the serial feeds and relay them to talkers that emit feeds to clients.

A listener needs a URL (domain or IP) and a port number to function. When active, it will simultaneously pass all received data from that endpoint to the talkers defined in its settings.

To create a listener, click the green plus icon on the right. 



2020, M/Y Esperanza PD6464

