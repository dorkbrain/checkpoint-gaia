#!/usr/bin/env python
import os

interfaces = {}
link_result = os.popen("ip -o link show").read()
for link_line in link_result.splitlines():
  ifname = link_line.split()[1].split('@')[0]
  if ifname.endswith(':'):
    ifname = ifname[:-1]

  if not ifname.startswith('lo'):
    try:
      with open('/sys/class/net/' + ifname + '/address', 'r') as file:
        interfaces[ifname] = {'hwaddr': file.read().strip()}
    except:
        interfaces[ifname] = {'hwaddr': '?'}

    try:
      with open('/sys/class/net/' + ifname + '/speed', 'r') as file:
        interfaces[ifname]['speed'] = file.read().strip() + 'Mb/s'
    except:
      interfaces[ifname]['speed'] = '?'

    try:
      with open('/sys/class/net/' + ifname + '/duplex', 'r') as file:
        interfaces[ifname]['speed'] += ' ' + file.read().strip()
    except:
      interfaces[ifname]['speed'] += ' ?'

    try:
      with open('/sys/class/net/' + ifname + '/carrier', 'r') as file:
        link_value = file.read().strip()
        if link_value == '1':
          interfaces[ifname]['link'] = 'yes'
        else:
          interfaces[ifname]['link'] = 'no'
    except:
      interfaces[ifname]['link'] = '?'

    interfaces[ifname]['auto'] = '?'
    ethtool_result = os.popen("/usr/sbin/ethtool " + ifname + " 2>/dev/null | grep 'Auto-negotiation'").read()
    for ethtool_line in ethtool_result.splitlines():
      ethtool = ethtool_line.strip().split()
      if ethtool[0].startswith('Auto-negotiation:'):
        if ethtool[1] == 'on':
          interfaces[ifname]['auto'] = 'Yes'
        else:
          interfaces[ifname]['auto'] = 'No'

    interfaces[ifname]['ifaddr'] = '?'
    addr_result = os.popen("ip -o -4 address show dev " + ifname).read()
    for addr_line in addr_result.splitlines():
      interfaces[ifname]['ifaddr'] = addr_line.split()[3]


out_format = "%-20s%-20s%-20s%-6s%-18s%s"
print(out_format % ('Name', 'IPv4', 'MAC', 'Link', 'Speed', 'Auto'))
for ifname in sorted(interfaces):
  ifinfo = interfaces[ifname]
  print(out_format % (ifname, ifinfo['ifaddr'], ifinfo['hwaddr'], ifinfo['link'], ifinfo['speed'], ifinfo['auto']))

raw_in = vars(__builtins__).get('raw_input', input)
if_capture = raw_in('Type an interface name: ')

if if_capture:
  print('Waiting for a CDPv2/LLDP packet on %s for up to 90s . . .' % if_capture)
  dump = os.popen('timeout 90s tcpdump -nnvv -s 1500 -c 1 -i %s "ether[20:2] == 0x2000 or ether proto 0x88cc" 2>/dev/null' % if_capture).read()
  nextline = ''
  packet_type = 'unknown'
  sysname = 'unknown'
  portid = 'unknown'
  firstline = True
  for line in dump.splitlines():
    if firstline:
      firstline = False
      if 'LLDP,' in line:
        packet_type = 'LLDP'
      if 'CDPv2,' in line:
        packet_type = 'CDPv2'
    else:
      if packet_type == 'LLDP':
        if nextline == 'port-id':
          nextline = ''
          portid = line.split()[-1]
        else:
          if line.strip().startswith('Port ID'):
            nextline = 'port-id'
          if line.strip().startswith('System Name'):
            sysname = line.split()[-1]
      if packet_type == 'CDPv2':
        if line.strip().startswith('Device-ID'):
          sysname = line.split()[-1].replace("'", "")
        if line.strip().startswith('Port-ID'):
          portid = line.split()[-1].replace("'", "")

  print(packet_type, sysname, portid)
