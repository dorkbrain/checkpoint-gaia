import subprocess
import re
import tempfile


table_format = '{:<16} {:<12} {:<7} {:<7} {:<12} {:<9} {:<14} {:<16} {:<6} {}'
table_header = table_format.format("Peer IP", "ASN", "Routes", "ActRts", "State", "Uptime", "Gateway NIC", "Cluster VIP", "BFD", "Peer Comment").strip()


def run_clish(command, vsid=-1):
  with tempfile.NamedTemporaryFile('w+') as tmp:
    if int(vsid) != -1:
      tmp.write(f'set virtual-system {vsid}\n')
    tmp.write(command)
    tmp.flush()
    proc = subprocess.run(["clish", "-i", "-f", tmp.name], capture_output=True)
    proc.stdout = [line.strip() for line in proc.stdout.decode().splitlines()]
  return proc.stdout


def run_command(command):
  proc = subprocess.run(command.split(" "), capture_output=True)
  return [line.strip() for line in proc.stdout.decode().splitlines()]


def peer_key(text):
  tempText = text.split()
  asn = tempText[1].split(".")
  if len(asn) > 1:
    asn = f'{asn[0].zfill(5)}{asn[1].zfill(5)}'
  else:
    asn = f'00000{asn[0].zfill(5)}'
  ip = "".join(i.zfill(3) for i in tempText[0].split("."))
  return f'{asn}{ip}'


def get_bgp_status(filter=""):
  re_vsid = r"vsid (?P<vsid>\d+):"
  re_vips = r"(?P<ifname>[\w\.\-]+)\s+(?P<ifaddr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
  re_peers = r"(?P<PeerID>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(?P<ASN>[\d\.]+)\s+(?P<Routes>\d+)\s+(?P<ActRts>\d+)\s+(?P<State>\w+)\s+(?P<InUpds>\d+)\s+(?P<OutUpds>\d+)\s+(?P<Uptime>[\w\:]+)"
  re_config = r"set bgp external remote-as (?P<ASN>[\d\.]+) description (?P<Comment>.*)"
  re_route = r".* dev (?P<iface>[\w\.\-]+)"
  re_bfd = r"^(?P<ipaddr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*BFD.*(?P<status>Yes|No|n\/a)$"
  
  vips_proc = run_command("cphaprob -a if")
  
  vsid = 0
  vips = {}
  peers = {}
  
  for line in vips_proc:
    vsidResult = re.search(re_vsid, line)
    vipResult = re.search(re_vips, line)
    if vsidResult:
      vsid = vsidResult.groupdict()["vsid"]
    if vipResult:
      vips[vipResult.groupdict()["ifname"]] = vipResult.groupdict()["ifaddr"]
  
  config_proc = run_clish("show configuration bgp", vsid)
  peers_proc = run_clish("show bgp peers", vsid)
  peers_proc = [line for line in peers_proc if re.search(re_peers, line)]
  peers_proc.sort(key=peer_key)
  bfd_proc = run_clish("show ip-reachability-detection")

  for line in peers_proc:
    peerResult = re.search(re_peers, line)
    if peerResult:
      route_proc = run_command(f"ip route get {peerResult.groupdict()['PeerID']}")[0]
      thisComment = ""
      for line in config_proc:
        if peerResult.groupdict()["ASN"] in line:
          configResult = re.search(re_config, line)
          if configResult:
            thisComment = configResult.groupdict()["Comment"].replace('"', '')
          
      thisBFD = "n/a"
      for line in bfd_proc:
        bfd_result = re.search(re_bfd, line, re.IGNORECASE)
        if bfd_result:
          if bfd_result.groupdict()["ipaddr"] == peerResult.groupdict()["PeerID"]:
            if bfd_result.groupdict()["status"].lower() == "no":
              thisBFD = "Down"
            elif bfd_result.groupdict()["status"].lower() == "yes":
              thisBFD = "Up"

      routeResult = re.search(re_route, route_proc)
      peers[peerResult.groupdict()["PeerID"]] = {
        "asn": peerResult.groupdict()["ASN"],
        "routes": peerResult.groupdict()["Routes"],
        "active": peerResult.groupdict()["ActRts"],
        "state": peerResult.groupdict()["State"],
        "uptime": peerResult.groupdict()["Uptime"],
        "iface": routeResult.groupdict()["iface"],
        "vip": vips[routeResult.groupdict()["iface"]],
        "bfd": thisBFD,
        "comment": thisComment
      }
  
  output_list = [table_header]
  if len(peers) > 0:
    for peerID, peer in peers.items():
      output_item = table_format.format(peerID, peer["asn"], peer["routes"], peer["active"], peer["state"], peer["uptime"], peer["iface"], peer["vip"], peer["bfd"], peer["comment"])
      if filter:
        if filter.lower() in output_item.lower():
          output_list.append(output_item)
      else:
        output_list.append(output_item)
  else:
    output_list.append("No BGP peers found")
  
  split_width = len(max(output_list, key=len))
  output_list.insert(1, "="*split_width)

  return "\n".join(output_list).strip()
