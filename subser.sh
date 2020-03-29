#!/bin/bash
# this script takes the subser.tmp file as a template
# and modifies it to submit the job
# by creating the corresponding qsub submission file
# and then submitting it to the queue
# all it takes is the inputfilename as the argument
# usage: ./subser.sh myinputfilenameforstupidserpent.inp
# the filename has to end with .inp
#
cp subser.tmp $1.sh
outname="$(basename $1 .inp).out"
sed -i "s/INPNAME/$1/" "$1.sh" 
sed -i "s/OUTNAME/$outname/" "$1.sh" 
qsub "$1.sh"
