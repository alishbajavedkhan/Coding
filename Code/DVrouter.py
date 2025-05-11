"""
DVrouter: Implementation of the Distance Vector Routing Protocol.

This module defines the `DVrouter` class, which inherits from the `Router` class.
The `DVrouter` class is responsible for handling distance vector updates, packet
processing, and routing decisions in a network simulation. It uses periodic
broadcasts to propagate the distance vector to all neighbor_node.

Class:
    DVrouter: Implements distance vector routing protocol methods for:
        - Handling packets
        - Managing link changes
        - Periodic updates based on time
        - Debugging
"""


# from collections import defaultdict
from json import dumps, loads
from router import Router
from packet import Packet
# import dijkstar
# import networkx
# from copy import deepcopy

#only maingtains info self and immediate neighbour
#router update its own state

class DVrouter(Router):
    """
    Distance Vector Routing Protocol Implementation.

    Handles distance vector updates, packet processing, and routing decisions.
    """

    def __init__(self, addr, heartbeat_time):
        """
        Initialize the DVrouter instance.

        Args:
            addr: The address of the router.
            heartbeat_time: Time interval for broadcasting distance vectors.
        """
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        """Hints: initialize local state."""
        self.link = {}
        self.neighbor_node = {}
        self.distance = {self.addr: (0, None)} # distance to itself is 0
        self.unreachable = 16  #infinity

    def handle_packet(self, port, packet: Packet):
        """
        Process an incoming packet.

        Args:
            port: The port on which the packet was received.
            packet: The packet to process.

        If the packet is a normal data packet:
            - Check if the forwarding table contains the packet's destinationination address.
            - Send the packet based on the forwarding table.
        If the packet is a routing packet:
            - Check if the received distance vector is different.
            - If the received distance vector is different:
                - Update the local copy of the distance vector.
                - Update the distance vector of this router.
                - Update the forwarding table.
                - Broadcast the distance vector of this router to neighbor_node.
        """
        if packet.is_traceroute():
            dst = packet.dstAddr
            if dst in self.distance:
                dist, next = self.distance[dst]
                if dist < self.unreachable and next in self.neighbor_node:
                    self.send(self.neighbor_node[next][0], packet)
            #forward is valid route drop if invalid route
        elif packet.isRouting():
            #process neighbour dv and then update local table for change in path
            try:
                n_addr = packet.srcAddr
                if n_addr not in self.neighbor_node:
                    return
                neighbour_dv = self.neighbor_node[n_addr][1]
                rcvd = loads(packet.getContent())
                update_dv = False

                for dst, dv_cost in rcvd.items():
                    dv = dv_cost + neighbour_dv
                    if dv >= self.unreachable:
                        dv = self.unreachable

                    current_dv, next_node = self.distance.get(dst, (self.unreachable, None))
                    if (dv < current_dv) or (next_node == n_addr):
                        if dv != current_dv:
                            self.distance[dst] = (dv, n_addr)
                            update_dv = True

                current_link, _ = self.distance.get(n_addr, (self.unreachable, None))
                if neighbour_dv < current_link:
                    self.distance[n_addr] = (neighbour_dv, n_addr)
                    update_dv = True

                if update_dv:
                    self.transmit_distance(poison_rev=True)  
            except Exception as e:
                print(f"error: {e}")

    def handle_new_link(self, port, endpoint, dist):
        """
        Handle the establishment of a new link.

        Args:
            port: The port number of the new link.
            endpoint: The endpoint address of the new link.
            dist: The dist of the new link.

        This method should:
            - Update the distance vector of this router.
            - Update the forwarding table.
            - Broadcast the distance vector of this router to neighbor_node.
        """
        self.distance[endpoint] = (dist, endpoint)
        self.neighbor_node[endpoint] = (port, dist)
        self.link[port] = (endpoint, dist)
        #send updated dv and enable poison reverse
        self.transmit_distance(poison_rev=True)

    def handle_remove_link(self, port):
        """
        Handle the removal of a link.

        Args:
            port: The port number of the removed link.

        This method should:
            - Update the distance vector of this router.
            - Update the forwarding table.
            - Broadcast the distance vector of this router to neighbor_node.
        """
        #remove mapping
        if port not in self.link:
            return
        endpoint, _ = self.link[port]
        del self.link[port]
        if endpoint in self.neighbor_node:
            del self.neighbor_node[endpoint]
        #remove neighbour enrty, next hop 
        update_dv = False
        for dst in list(self.distance.keys()):
            _, n = self.distance[dst]
            if n == endpoint:
            #cost to unreachable
                self.distance[dst] = (self.unreachable, None)
                update_dv = True

        if update_dv:
            self.transmit_distance(poison_rev=True)

    def handle_time(self, time_milli_secs):
        """
        Handle periodic tasks based on the current time.

        Args:
            time_milli_secs: The current time in milliseconds.

        If the time since the last broadcast exceeds the heartbeat interval:
            - Broadcast the distance vector of this router to neighbor_node.
        """
        if time_milli_secs - self.last_time >= self.heartbeat_time:
            self.last_time = time_milli_secs
            #prevent loop so poison
            self.transmit_distance(poison_rev=True)


    def transmit_distance(self, poison_rev=False):
        """
        transmit dv to neighbors
        """
        #packet contents
        send_pkt = []
        for neighbor, (port, _) in self.neighbor_node.items():
            neighbour_dv = {
                dst: self.unreachable if (poison_rev and next_hop == neighbor) else dist
                for dst, (dist, next_hop) in self.distance.items()
            }
            send_pkt.append((port, neighbour_dv))

        #do all transmissions
        for port, neighbour_dv in send_pkt:
            pkt = Packet(Packet.ROUTING, self.addr, 'ALL', dumps(neighbour_dv))
            self.send(port, pkt.copy())

    def debug_string(self):
        """
        Generate a string for debugging in the network visualizer.

        Returns:
            str: A debug string representing the router's state.
        """
        debug_output = f"DV: {self.distance}, Links: {self.link}"
        return debug_output
