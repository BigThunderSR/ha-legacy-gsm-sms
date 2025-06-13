#!/command/with-contenv bashio

# This script is executed at container startup to help debug s6-overlay issues

# Log system information
echo "====== DEBUG INFORMATION ======"
echo "Current date: $(date)"
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Process ID: $$"
echo "Parent Process ID: $PPID"
echo "Environment variables:"
env | sort
echo 
echo "Current processes:"
ps aux
echo
echo "Mount points:"
mount
echo
echo "Directory structure:"
ls -la /
ls -la /etc
ls -la /etc/services.d
ls -la /etc/services.d/gsm_sms
ls -la /usr/bin
echo
echo "S6 structure:"
ls -la /etc/s6-overlay || echo "No /etc/s6-overlay directory"
ls -la /run/s6 || echo "No /run/s6 directory"
ls -la /run/s6/services || echo "No /run/s6/services directory"
echo
echo "======= END DEBUG INFO ======="
