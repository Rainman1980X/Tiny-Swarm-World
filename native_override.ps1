$cmd = @'
set -e
cd /home/tsw/Tiny-Swarm-World
printf "export TSW_PORTAINER_ADMIN_PASSWORD='NativeOverride-Portainer-2026!'
export TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD='NativeOverride-Infisical-2026!'
" | tee /home/tsw/.local/state/tiny-swarm-world/native-override.env >/dev/null
chmod 600 /home/tsw/.local/state/tiny-swarm-world/native-override.env
set -a
. /home/tsw/.local/state/tiny-swarm-world/native-live-installation.env
set +a
export TSW_BOOTSTRAP_SECRET_ENV_FILE=/home/tsw/.local/state/tiny-swarm-world/native-override.env
export TSW_LXC_ALLOW_PRIVILEGED_SWARM_INGRESS=1
./install.sh --headless --confirm-reset --non-interactive-live-approval
'@
echo tsw | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null tsw@172.26.4.8 $cmd
