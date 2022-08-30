## curl alias
alias curl=curl_cli

## Include context name in VSX prompt
if [[ $(vsx get 2>&1 | grep "Current context is") ]]; then
grep -q '#VSXPROMPT:' /etc/bashrc || cat<<'EOF'>> /etc/bashrc
#VSXPROMPT: Include VSX context name in the prompt
if [[ -f $FWDIR/conf/vsname ]]; then
  [[ -f /proc/self/vrf ]] && export PS1='[Expert@`cat $FWDIR/conf/vsname`:`cat /proc/self/vrf`]# '
  [[ -f /proc/self/nsid ]] && export PS1='[Expert@`cat $FWDIR/conf/vsname`:`cat /proc/self/nsid`]# '
fi
EOF
fi

function vcd() {
  ## Change to vsenv based on name
  if [[ -z "$1" ]]; then
    vsenv 0
  else
    for ctx in /opt/CPsuite-R80*/fw1/CTX/CTX*/conf/vsname; do
      ctxname=$(cat $ctx)
      if [[ ${ctxname,,} == *${1,,} || ${ctxname,,} == *${1,,}-0 ]]; then
        if [[ $ctx =~ '.*\/CTX([0-9]{5})\/.*' ]]; then
          ctxnum=$(echo ${BASH_REMATCH[1]##+(0)} | sed 's/^0*//')
          vsenv $ctxnum
          return 0
        fi
      fi
    done
    echo "Couldn't find '$1'"
  fi
}

## Display installed Checkpoint version and HFA take
function cpver() {
  echo "$(cat /etc/cp-release) take $(cpinfo -y fw1 2>/dev/null | grep -i Jumbo | grep -i Take | awk '{print $3}')"
}

## Shortcut to watch HA status of cluster
function hawatch() {
  watch -d cphaprob stat
}

## Shortcut to watch BGP status
function bgpwatch() {
  watch -cd bgpstat
}

## Shortcut to watch HA and BGP status
function habgpwatch() {
  watch -cd 'cphaprob stat | head -11; bgpstat'
}

## Returns the newest installed version of python
function py() {
  # Import Checkpoint environment
  . /etc/profile.d/CP.sh

  for p in $FWDIR/Python/bin/python{3,2}; do
    if [[ -f $p ]]; then
      echo $p
      return 0
    fi
  done

  echo "Couldn't find python installed in $FWDIR"
  return 1
}
