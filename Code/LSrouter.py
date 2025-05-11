
"""
LSrouter: Implementation of the Link State Routing Protocol.

This module defines the `LSrouter` class, which inherits from the `Router` class.
The `LSrouter` class is responsible for handling link state updates, packet processing,
and routing decisions in a network simulation. It uses periodic broadcasts to 
propagate the link state to all neighbors.

Class:
    LSrouter: Implements link state routing protocol methods for:
        - Handling packets
        - Managing link changes
        - Periodic updates based on time
        - Debugging
"""

# from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads
from dijkstar import Graph, find_path, algorithm

# import dijkstar
# import networkx
# from copy import deepcopy

#dijkstar- shortest path from one point to another
#shortest path- least cost path
#conflicting info about packets
#compares updated sequence number(higher) and discard other one- slow path
#LS packet includes seq num and info about neighbours
#change in topology- link added, router added, router gone down
#inherits from the router class
#use only one dijkstar or netwrokx


class LSrouter(Router):
    """Link state routing protocol implementation."""

    def __init__(self, addr, heartbeat_time):
        """
        Initialize the LSrouter instance.

        Args:
            addr: The address of the router.
            heartbeat_time: Time interval for broadcasting link states.
        """
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeat_time = heartbeat_time #propograte linkstate again
        self.last_time = 0
        self.seq_num = 0
        self.link = {}
        self.l_state = {addr: {'seq': self.seq_num, 'links': {}}}
        self.routing_table = {}
        """Hints: initialize local state."""

        #routing table, graph -> dijkstar -> unweight/weight, weighted/unweighted

    def handle_packet(self, port, packet: Packet):
        """
        Process an incoming packet.

        Args:
            port: The port on which the packet was received.
            packet: The packet to process.

        If the packet is a normal data packet:
            - Check if the forwarding table contains the packet's destination address.
            - Send the packet based on the forwarding table.
        If the packet is a routing packet:
            - Check the sequence number.
            - If the sequence number is higher and the received link state is different:
                - Update the local copy of the link state.
                - Update the forwarding table.
                - Broadcast the packet to other neighbors.
        """

        #links indexed by port- which port to send it on- take care of mapping
        #not allowed to access from DSrouter- figure out the route
        if packet.isRouting():
            try:
                routing_data = loads(packet.getContent())
                source = routing_data['source']
                seq = routing_data['seq']
                links = routing_data['links']
                #flooding to all ports but not the one it came from
                if source not in self.l_state or seq > self.l_state[source]['seq']:
                    self.l_state[source] = {'seq': seq,'links': links}
                    for i in self.link:
                        if i != port:
                            self.send(i, packet.copy())
                    self.calculate_route()
            except:
                pass
        elif packet.is_traceroute():
            dst = packet.dstAddr
            if dst in self.routing_table:
                self.send(self.routing_table[dst], packet)

    def handle_new_link(self, port, endpoint, cost):
        #not for exiting link
        """
        Handle the establishment of a new link.

        Args:
            port: The port number of the new link.
            endpoint: The endpoint address of the new link.
            cost: The cost of the new link.

        This method should:
            - Update the forwarding table.
            - Broadcast the new link state of this router to all neighbors.
        """
        #local link state
        self.l_state[self.addr]['links'][endpoint] = cost
        self.seq_num += 1
        self.l_state[self.addr]['seq'] = self.seq_num
        self.link[port] = (endpoint, cost)
        #flood changes and recalculate
        self.calculate_route()
        self.flooding_to_neighbours()

    def handle_remove_link(self, port):
        """
        Handle the removal of a link.

        Args:
            port: The port number of the removed link.

        This method should:
            - Update the forwarding table.
            - Broadcast the new link state of this router to all neighbors.
        """
        if port not in self.link:
            return

        endpoint, _ = self.link[port]
        self.seq_num += 1
        if endpoint in self.l_state[self.addr]['links']:
            del self.l_state[self.addr]['links'][endpoint]
        self.l_state[self.addr]['seq'] = self.seq_num
        del self.link[port]
        #flood and recalculate
        self.flooding_to_neighbours()
        self.calculate_route()

    def handle_time(self, time_milli_secs):
        #heartbeat and periodic
        """
        Handle periodic tasks based on the current time.

        Args:
            time_milli_secs: The current time in milliseconds.

        If the time since the last broadcast exceeds the heartbeat interval:
            - Broadcast the link state of this router to all neighbors.
        """
        if time_milli_secs - self.last_time >= self.heartbeat_time:
            self.last_time = time_milli_secs
            self.seq_num += 1
            self.l_state[self.addr]['seq'] = self.seq_num
            self.flooding_to_neighbours()

    def flooding_to_neighbours(self):
        """
        flood the link state to all neighbors
        """
        update = {
            'source': self.addr,
            'seq': self.seq_num,
            'links': self.l_state[self.addr]['links']
        }
        update_packet = Packet(Packet.ROUTING, self.addr, 'ALL', dumps(update))
        for i in self.link:
            self.send(i, update_packet.copy())

    def calculate_route(self):
        """
        calculate the shortest path
        """
        graph = Graph()
        #all routers
        for nodes, state in self.l_state.items():
            for neighbour_node, c in state['links'].items():
                graph.add_edge(nodes, neighbour_node, c)
                graph.add_edge(neighbour_node, nodes, c)

        self.routing_table= {}
        dst_nodes = set()
        for nodes in self.l_state:
            dst_nodes.add(nodes)
            dst_nodes.update(self.l_state[nodes]['links'].keys())
        #shortest paths
        for dest in dst_nodes:
            #skip self
            if dest == self.addr:
                continue
            try:
                shortest_path = find_path(graph, self.addr, dest)
                #first hop
                next_hop = shortest_path.nodes[1]
                for port, (n, _) in self.link.items():
                    if n == next_hop:
                        self.routing_table[dest] = port
                        break
            except (algorithm.NoPathError, KeyError):
                pass

    def debug_string(self):
        """
        Generate a string for debugging in the network visualizer.

        Returns:
            str: A debug string representing the router's state.
        """
        #return "routing table info, link states info, for debgugging"
        debug = {
        'routing_table': self.routing_table,
        'sequence_number': self.seq_num,
        }
        debug_output = (
            f"router {self.addr} State:\n"
            f"routing table: {debug['routing_table']}\n"
            f"sequence: {debug['sequence_number']}\n"
        )
        return debug_output

"""
my_packet= Packet(Packet.ROUTING, srcAddr, dstAddr, content)
TRACEROUTE or ROUTING

dumps and loads
define dictioninary
x- LS packet for A
x=
(B: 3
C: 4
)

converts into string
X_string= dumps(X) - turns into string
loads(X_string)- turns string back into a dictionary
sending-
self.send(port,packet)

in handle packet port tells you where you are receiving it from- so avoid loops

"""