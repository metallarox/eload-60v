#!/bin/bash
set -e
R=/home/claude/kicad10/squashfs-root
export KICAD10_SYMBOL_DIR=$R/usr/share/kicad/symbols KICAD10_FOOTPRINT_DIR=$R/usr/share/kicad/footprints
P=/home/claude/out/carico_attivo/carico_attivo.kicad_pcb
cd /home/claude/pcb10
$R/AppRun python3.11 build_pcb.py 2>&1 | grep -v assert | tail -1
$R/AppRun kicad-cli pcb drc --refill-zones --save-board -o /tmp/drc_pre.rpt $P >/dev/null 2>&1
LOCKALL=1 $R/AppRun python3.11 autoroute.py --norun 2>&1 | grep -v assert | tail -1
rm -f /tmp/out.ses
xvfb-run -a java -jar /home/claude/freerouting.jar -de /tmp/in2.dsn -do /tmp/out.ses -mp ${PASSES:-25} > /tmp/ar.log 2>&1 || true
$R/AppRun python3.11 import_ses.py /tmp/out.ses 2>&1 | grep -v assert | tail -1
$R/AppRun kicad-cli pcb drc --refill-zones --save-board --schematic-parity --severity-all -o /tmp/drc10.rpt $P 2>&1 | tail -1
grep -o "^\[[a-z_]*\]" /tmp/drc10.rpt | sort | uniq -c
grep -A4 "^\[unconnected_items\]" /tmp/drc10.rpt | grep "@" || true
