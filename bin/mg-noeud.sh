#! /bin/sh

### BEGIN INIT INFO
# Provides:          mg-noeud
# Required-Start:    $local_fs
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:
# Short-Description: Noeud millegrilles
# Description: Demarre le noeud millegrilles avec les senseurs et affichages.
### END INIT INFO

COMMAND=/opt/millegrilles/bin/noeud.sh

set -e

case "$1" in
  start)
        $COMMAND start
	;;
  restart)
        $COMMAND restart
	;;
  stop)
        $COMMAND stop
	;;
  *)
	echo "Usage: $N {start|stop|restart}" >&2
	exit 1
	;;
esac

exit 0
