#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 12:18:08 2020

@author: agoluogl
"""
import os
import time

#%% Make & Run MCNP Input Decks
#remove existing files to redo
try:
    os.system("rm hw4_2_*")
except OSError:
    print("OSError, No Existing Data File")

#create datafile
with open("hw4_2_table.csv","w") as datafile:
    datafile.write("Source Dimension,Distance (cm),F5 Tally\n")
    
distances=(1,2,4,8,16,32,64,128,256) #distance from source in cm
f5tally_list=[] #total point flux
dim=(0,1,2,3) #dimension of source

for x,i in enumerate(dim):
    for j,distance in enumerate(distances):
    
        prefix="hw4_2_"
        prefix+="{}".format(i)
        prefix+="{}".format(distance)
        file_in=prefix+".inp"
        file_out=prefix+".out"
        script=prefix+".sh"
    
        myfile="""
NE 406 HW 4.2
c *****CELLS CARDS*****
1 0         -1    imp:p=1          $ cell 1, material void, no density, inside surface 1, track photons b/c why not
2 0          1 -2 imp:p=1          $ cell 2, material void, no density, outside surface 1 inside surface 2, track photons
3 0          2    imp:p=0          $ cell 3, material void, no density, outside surface 2, kill photons

c *****SURFACE CARDS*****
1 rcc  0 0   {distance}            $ surface 1 (not necessary but dont want to delete), disk {distance} cm above origin
       0 0   1                     $ height of 1 cm 
       5                           $ radius of 5 cm 
2 sph  0 0 0                       $ surface 2, sphere centered at origin, to encompass point source and disk
       300                         $ arbitrary radius to encompass point source 

c *****DATA CARDS*****
mode p                             $ track photons"""


        if i==0:
            myfile+="""c POINT SOURCE
sdef par=2 pos=0 0 0               $ isotropic photon point source at origin"""

        if i==1:
            myfile+="""c 1D LINE SOURCE
sdef par=2 pos=0 0 0 x=d1 y=0 z=0  $ line photon source at origin
si1  -4   4                        $ xmin and xmax for line
sp1  -21  0                        $ uniform sampling on line following x^0"""

        if i==2:
            myfile+="""c 2D AREA SOURCE
sdef par=2 pos=0 0 0 x=d1 y=d2 z=0 $ square area photon source at origin
si1  -4   4                        $ xmin and xmax for square
sp1   0   1                        $ weighting for x sampling: here constant
si2  -2   2                        $ ymin and ymax for square
sp2   0   1                        $ weighting for y sampling: here constant"""

        if i==3:
            myfile+="""c 3D VOLUMETRIC SOURCE
sdef par=2 pos=0 0 0 x=d1 y=d2 z=d3 $ cube volume photon source at origin
si1  -4   4                        $ xmin and xmax for cube
sp1   0   1                        $ weighting for x sampling: here constant
si2  -2   2                        $ ymin and ymax for cube
sp2   0   1                        $ weighting for y sampling: here constant
si3  -1   1                        $ zmin and zmax for cube
sp3   0   1                        $ weighting for z sampling: here constant"""

        myfile+="""
f5:p 0 0 {distance} 0.1            $ point flux tally for photons at (0,0,{distance}), use 0.1 for radius where flux contribution will not be made
nps 1000000                        $ run 1,000,000 particles
c output naming convention: hw4_2_12.out (1D source, 2 cm away), hw4_2_364 (3D source, 64 cm away)"""

        myfile=myfile.format(**locals())
        with open(file_in,"w") as file:
            file.writelines(myfile[2:])
        
        myscript="""#!/bin/bash
#PBS -q fill
#PBS -V
#PBS -l nodes=1:ppn=8

module load intel/12.1.6
module load openmpi/1.6.5-intel-12.1
module load MCNP6/2.0

RTP=`date "+%R%N"`
cd $PBS_O_WORKDIR
mcnp6 TASKS 8 inp={file_in} outp={file_out} runtpe=/tmp/$RTP
rm /tmp/$RTP"""

        myscript=myscript.format(**locals())
        with open(script,"w") as file:
            file.write(myscript)

        try:
            os.system("qsub {}".format(script))
        except OSError:
            print("OSError, I do not like that.")
            
        
        print("Submitting File ",i,distance)
        
 
print("-----Files Submitted!-----")

#%% Fetch Tally Data

time.sleep(20) #let MCNP files run

for x,i in enumerate(dim):
    for j,distance in enumerate(distances):
    
        prefix="hw4_2_"
        prefix+="{}".format(i)
        prefix+="{}".format(distance)
        file_in=prefix+".inp"
        file_out=prefix+".out"

        with open(file_out) as output:
            for line in output:
                if "detector located" in line:
                    f5tally=(next(output, '').strip())
                    break
    
        with open("hw4_2_table.csv","a+") as datafile:
            datafile.write("{},{},{}\n".format(i,distance,f5tally)) 
            
try:
    os.system("rm *.sh")
except OSError:
    print("OSError, cannot remove scripts")        

print("-----Done!-----")

