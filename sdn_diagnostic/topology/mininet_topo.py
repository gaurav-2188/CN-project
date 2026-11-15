#!/usr/bin/env python3
"""
Deliverable 1 & 2: Mininet Network Topology Implementation
Matches the 4-switch, 4-host multi-path redundant SDN topology:

        h1 \                           / h3
            -- [s1] === [s2] === [s4] --
        h2 /    | \             / |    \ h4
                |   ==== [s3] === |

Path A (Primary):    h1 <-> s1 <-> s2 <-> s4 <-> h3
Path B (Alternate):  h1 <-> s1 <-> s3 <-> s4 <-> h3
"""

try:
    from mininet.topo import Topo
    from mininet.net import Mininet
    from mininet.node import RemoteController, OVSSwitch
    from mininet.cli import CLI
    from mininet.log import setLogLevel, info
    from mininet.link import TCLink
    HAS_MININET = True
except ImportError:
    HAS_MININET = False


class MultiPathSDNTopo(Topo if HAS_MININET else object):
    """Mininet Custom Topology for Deliverable 1 & 2."""
    def build(self, **_opts):
        # 1. Add Switches
        s1 = self.addSwitch('s1', dpid='0000000000000001')
        s2 = self.addSwitch('s2', dpid='0000000000000002')
        s3 = self.addSwitch('s3', dpid='0000000000000003')
        s4 = self.addSwitch('s4', dpid='0000000000000004')

        # 2. Add Hosts
        h1 = self.addHost('h1', ip='10.0.0.101/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.102/24', mac='00:00:00:00:00:02')
        h3 = self.addHost('h3', ip='10.0.0.103/24', mac='00:00:00:00:00:03')
        h4 = self.addHost('h4', ip='10.0.0.104/24', mac='00:00:00:00:00:04')

        # 3. Connect Hosts to Edge Switches
        self.addLink(h1, s1, port1=0, port2=1)
        self.addLink(h2, s1, port1=0, port2=4)
        self.addLink(h3, s4, port1=0, port2=3)
        self.addLink(h4, s4, port1=0, port2=4)

        # 4. Inter-Switch Links with configured delay/bandwidth
        # Primary Path via s2
        self.addLink(s1, s2, port1=2, port2=1, delay='4.5ms', bw=100)
        self.addLink(s2, s4, port1=2, port2=1, delay='5.0ms', bw=100)

        # Alternate Path via s3
        self.addLink(s1, s3, port1=3, port2=1, delay='8.0ms', bw=100)
        self.addLink(s3, s4, port1=2, port2=2, delay='8.5ms', bw=100)

        # Cross Link between core switches
        self.addLink(s2, s3, port1=3, port2=3, delay='3.0ms', bw=100)


def run_mininet_demo(controller_ip='127.0.0.1', controller_port=6633):
    if not HAS_MININET:
        print('[!] Mininet is not installed in this environment.')
        print('    Run this script inside a Linux VM or container with Mininet installed.')
        return

    setLogLevel('info')
    info('*** Creating Multi-Path SDN Topology\n')
    topo = MultiPathSDNTopo()
    
    info('*** Connecting to SDN Remote Controller\n')
    controller = RemoteController('c0', ip=controller_ip, port=controller_port)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=controller, link=TCLink)

    info('*** Starting Network\n')
    net.start()

    info('*** Testing Basic Connectivity (h1 -> h3)\n')
    h1 = net.get('h1')
    h3 = net.get('h3')
    net.ping([h1, h3])

    info('*** Entering Mininet CLI (Type exit to quit)\n')
    CLI(net)

    info('*** Stopping Network\n')
    net.stop()

topos = {'multipath_sdn': (lambda: MultiPathSDNTopo())}

if __name__ == '__main__':
    run_mininet_demo()
