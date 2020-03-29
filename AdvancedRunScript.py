#!/usr/bin/env python2.7
import numpy as np
import os
import time
import platform
import subprocess
import glob
import sys
import shutil
import re
# Originally written by Dallas Moser: ARSv1.1_alpha4.py
## Functions used throughout the code 
def remove_file(file_string):
	"""
	Function to remove a file (check if file exists, if yes, remove).
	File_string can be a single filename or use unix-style wildcards (i.e. '*.out')
	"""

#	pull the filename or filenames if using wildcard, this will also check if files exist
	file_list = glob.glob(file_string)

#	if the file/s exist, remove them, if not, don't worry about
	if file_list:
		for filename in glob.glob(file_string):
			os.remove(filename)
	else:
		pass

def remove_directory(dirname):
	"""
	Remove a directory (check if directory exists, if yes, remove)
	"""
	try:
		shutil.rmtree(dirname)
	except OSError:
		pass
	return


def write_scale_sub(input_prefix, input_name, task, final_structure):
	"""
	Function to write SCALE submission script given an input prefix (no extension) and input name
	"""
	current_working_dir = os.getcwd() # this is used because the standard output files don't print sometimes by default

#	form the unique job submission script
	job_sub = '''#!/bin/bash
#PBS -V
#PBS -l procs=1

prefix={input_prefix}
input={input_name}

# change to the directory that the script was submitted in
cd $PBS_O_WORKDIR

# run the input file
batch6.1 $input

echo -n $input", " > results.csv
if ! grep "best estimate system k-eff" $prefix.out; then
     echo "ERROR,  ERROR,  ERROR,  ERROR,  ERROR, ERROR" >> results.csv
else
     echo -n $(grep "best estimate system k-eff" $prefix.out | awk '{{print $6",", $10",", $6+2*$10","}}') >> results.csv
     echo -n " " >> results.csv
     echo -n $(grep "Energy of average" $prefix.out | awk '{{print $9",", $13}}') >> results.csv

     if grep "k-effective fails the chi\*\*2 test" $prefix.out; then
         echo ", Fail" >> results.csv
     else
         echo ", Pass" >> results.csv
     fi
fi

rm -r *.htmd
rm *.msg
rm *.html
rm -r applet_resources
'''

	if task == 1 and final_structure == 2:
		job_sub += 'cat results.csv >> ../final.csv'
	elif task ==1 and final_structure == 1:
		job_sub += 'cat results.csv >> ../final.csv\nrm results.csv\nmv * ..\nrm -r $PBS_O_WORKDIR'
	else:
		pass
#	grep "best estimate system k-eff" $prefix.out | awk '{{print $6, $10, $6+2*$10}} END {{if (NR == 0) print "ERROR ERROR ERROR"}}' >> results.txt
	return job_sub.format(**locals())


def write_mcnp_sub(input_prefix, input_name, task, final_structure):
	"""
	Function to write MCNP submission script given input prefix (no extension) and input name
	"""

	current_working_dir = os.getcwd() # this is used because the standard output files don't print sometimes by default

#	MCNP will only use 1/32 of one processor if --bind-to-core is used and 1 processor is requested
	processors = 1
	if processors == 1:
		run_line = "mpirun --bind-to-none -machinefile $PBS_NODEFILE mcnp6.mpi i=$input o=$prefix.out runtpe=$RTP"
	else:
		run_line = "mpirun --bind-to-none -machinefile $PBS_NODEFILE mcnp6.mpi i=$input o=$prefix.out runtpe=$RTP"

#	form the unique job submission script
	job_sub = '''#!/bin/bash
#PBS -V
#PBS -l procs={processors}

prefix={input_prefix}
input={input_name}
RTP=`date "+%R%N"`


# change to the directory that the script was submitted in
cd $PBS_O_WORKDIR

# run the input file
{run_line}

echo -n $input", " > results.csv
if ! grep "final result" $prefix.out; then
     echo "ERROR,   ERROR,  ERROR, ERROR" >> results.csv
else
    echo -n $(grep "final result" $prefix.out | awk '{{print $3",", $4",", $3+2*$4","}}') >> results.csv
    echo -n " " >> results.csv
    echo -n $(grep "average neutron lethargy" $prefix.out | awk '{{print $13}}') >> results.csv

    if grep "Source entropy convergence check passed" $prefix.out; then
        echo -n ", Pass" >> results.csv
    else
        echo -n ", Fail" >> results.csv
    fi

    if grep "same at the 95 percent" $prefix.out || grep "same at the 68 percent" $prefix.out; then
        echo ", Pass" >> results.csv
    else
        echo ", Fail" >> results.csv
    fi
fi

rm $RTP
rm src*
'''
	if task == 1 and final_structure == 2:
		job_sub += 'cat results.csv >> ../final.csv'
	elif task ==1 and final_structure == 1:
		job_sub += 'cat results.csv >> ../final.csv\nrm results.csv\nmv * ..\nrm -r $PBS_O_WORKDIR'
	else:
		pass

	return job_sub.format(**locals())


def check_job(job_id):
	"""
	Function to determine when submitted jobs have finished
	"""
#	initialize variables
	directory_list = []
	job_id_num = []
	subm_name = []
	to_remove = []
	running_list = []
	complete_list = []
	need_to_remove = False

#	parse job_id data into a more useful form
	for i in range(len(job_id)):
		directory_list.append(job_id[i][0])
		job_id_num.append(job_id[i][1])
		subm_name.append(job_id[i][2])
		running_list.append([directory_list[i], job_id_num[i], subm_name[i]])
	print "\nChecking directories for results.csv files\n"
	time.sleep(10)
	cycle = 1

#	check if the standard output file exists in each directory
	while len(complete_list) != len(directory_list):
		print "Jobs are running, check %d\n" % cycle
		for i in range(len(running_list)):
			os.chdir(running_list[i][0])
#			job_output_file = running_list[i][2] + ".o%s" % running_list[i][1]
#			done_file = running_list[i][1] + ".done"
			done_file = "results.csv"
			done_file_exists = os.path.isfile(done_file)
			if done_file_exists:  # and os.path.getsize(job_output_file) > 0: # if the output exists and contains data, take it out of the list of output to check
				complete_list.append(running_list[i])
				to_remove.append(running_list[i])
				need_to_remove = True
#				os.remove(done_file)
			os.chdir('..')
		if need_to_remove:
			for line in to_remove:
				running_list.remove(line)
			need_to_remove = False
		to_remove = []
		cycle += 1
		time.sleep(10)
	print "Jobs have finished!\n"

def test_question(question, options, lower_value, upper_value, custom_message=""):
	"""
	Function get user data and error test each response. lower_value and upper_value are the accepted option range.
	The question will be asked repeatedly until the user chooses a correct option.
	"""
	while True:
		try:
			answer = int(raw_input(question + options))
		except ValueError:
			print "\nTHAT WAS DEFINITELY NOT A NUMBER!!! "+"("+u"\u0CA0"+"_"+u"\u0CA0"+")\n"

		else:
			if lower_value <= answer <= upper_value:
				break
			else:
				if not custom_message:
					print "\nTHERE ARE ONLY %d OPTIONS ... " % upper_value +"("+u"\u0CA0"+"_"+u"\u0CA0"+")\n"
				else:
					print custom_message

	return answer

def get_code_type(input_name):
	"""
	Function to automatically get the code type depending on search terms: kcode for MCNP, and CSAS for SCALE
	1 is for SCALE, 2 is for MCNP, I plan on changing this later to be the actual names and not numbers
	"""
	code_type = 'UNKNOWN'
	mcnp_term = 'kcode'
	scale_term = 'csas'

	input_file = open(input_name).readlines()
	for line in input_file:
		if re.search(mcnp_term, line, re.IGNORECASE):
			code_type = 2
		elif re.search(scale_term, line, re.IGNORECASE):
			code_type = 1
		else:
			pass

	return code_type
		
def get_prefix(input_name, input_ext):
	"""
	Function to remove the input extension from an input name
	"""
##	first check to see if there are spaces in the provided input name, if yes, I don't want to deal with it
	if ' ' in input_name:
		print "Please don't use spaces in input names. They don't work right, I promise!"
		print "!!!EXITING!!!"
		quit()
	else:
		pass

##	start working on parsing the input name and extension
	input_prefix = ""                                    # initialize input prefix (filled in at the end)
	input_ext_split = [letter for letter in input_ext]   # split the extension string into a list of characters
	input_ext_split.pop(0)                               # remove the * that is prepended by ARS
	input_name_split = [letter for letter in input_name] # split the input name into a list of characters

##	find the location of wildcards and determine the true location of the extension (before or after input names)
#	beginning/end will determine where to remove the extension (from beginning or end of input_name)
	beginning = False
	end = False

#	keep track of which characters need to be removed from the input name
	characters_to_remove = ""

#	after removing the prepended *, if the first entry is not a * (meaning it's a letter or something else) and there are more *s, the extension is at the beginning of the input name
	if input_ext_split[0] != "*" and "*" in input_ext_split:
		beginning = True
		characters_to_remove = input_ext_split[0]
		if input_ext_split[1] == ".":
			characters_to_remove += input_ext_split[1]
		else:
			pass
	else:
		end = True
		for character in reversed(input_ext_split):
			if character == "*":
				break
			else:
				characters_to_remove += character

#	if only a * was inputed, no extension would be determined, so exit
	if not characters_to_remove:
		print "\nInput extensions characters could not be found ... EXITING!!!!!\n"
		quit()

#	if the extension is at the beginning of input name, remove that number of characters from the beginning
	if beginning:
		for character in characters_to_remove:
			input_name_split.pop(0)
#	if the extension is at the end (as god intended), remove that number of characters from the end
	elif end:
		for character in characters_to_remove:
			input_name_split.pop(-1)   # -1 tells pop to get rid of the last element in a list
	else:
		print "\nInput extension could not be located... EXITING!!!!!\n"

#	combine the split text into a single string
	for letter in input_name_split:
		input_prefix += letter
	
	return input_prefix


# Introduction to the script

print '''\n-------------------------------------------------------
          Welcome to Advanced Run Script v1.1_alpha4
-------------------------------------------------------'''

'''This script is used to run MCNP or SCALE input files on an HPC system that uses the MOAB job scheduling package\n\n''' 

# Check the operating system
op_sys = platform.system()
if op_sys != 'Linux':
	print "Sorry, this script is only made for Linux machines!"
	quit()

# Check if a settings file exists, if yes, run using those settings
settings_exists = os.path.isfile("settings.py")
if settings_exists:
	print '\033[1m'+'\n!!! A settings file was found, those settings will be used for this run !!!\n'+'\033[0m'
	print "To run with custom settings, please delete the settings.py file and run again\n"
	working_dir = os.getcwd()    # get current working directory
	sys.path.append(working_dir) # temporarily append working directory to python path for modules (really only important if used as a command not in the directory)
	from settings import *
	time.sleep(1)
else:
##	handle command line arguments
#	get command line arguments
	command_line_arguments = sys.argv

#	booleans to determine run mode
	automatic_code_type = False

#	if -a is specified, turn on automatic code type 
	if '-a' in command_line_arguments:
		automatic_code_type = True
		print "\033[1m" + "\n!!! Automatic code determination has been activated !!!\n" + "\033[0m"

# 	Print question instructions

	print '''Several questions will be asked, please answer by inputing the number (no extra characters)
of the line you wish to choose, then press ENTER.\n\n'''

# 	Ask the user what they would like to do with the program
	question1 = 'What would you like to do?\n'
	options1 = '''1) Just run inputs and quit (does not consolidate results, will end in subdirectories)
2) Run inputs and wait for the results (consolidates results, allows custom file structure)\n'''
	task = test_question(question1, options1, 1, 2)
	
# 	Ask user about initial input file structure 
	question2 = '\nHow are the inputs currently structured in the file system?\n'
	options2 = '''1) They are all in the same directory
2) They are each in their own subdirectories\n'''
	initial_structure = test_question(question2, options2, 1, 2)	

# 	Ask user about the preferred final file structure (if they choose to wait for the jobs to finish)
	question3 = '\nHow would you like the outputs to be structured in the file system?\n'
	options3 = '''1) All inputs and outputs in the same directory
2) Each input and output pair in their own subdirectories\n'''
	if task is 2:
		final_structure = test_question(question3, options3, 1, 2)
	else:
		final_structure = initial_structure

# 	Ask user what code they will be running (SCALE or MCNP), unless auto mode is activated
	question4 = '\nWhat code are you using?\n'
	options4 = '''1) SCALE (KENO)
2) MCNP\n'''
	if not automatic_code_type:
		input_code = test_question(question4, options4, 1, 2)
	else:
		input_code = 3
		pass

# 	Ask user about number of jobs and expected runtime
	question5 = '''\nHow many inputs would you like to run at one time? (1 processor a piece) 
(all inputs will run, but only the specified number will run at one time to save cluster space)\n'''
	options5 = '''1) Default (32 inputs [1 node])
2) Custom\n'''

	hpc_load = test_question(question5, options5, 1, 2)
	if hpc_load == 2:
		cycle_pause = test_question("Enter custom processor amount: ", "", 1, 1024, "THERE AREN'T EVEN THAT MANY PROCESSORS ON THE CLUSTER!!!!!")
	else:
		cycle_pause = 32

# 	Ask user what extension is used between all input files
	question6 = '\nWhat is the file extension that is common to all input files?\n'
	options6 = 'Type the file extension (ex. if all inputs end in .inp, type .inp and press ENTER)\n'

	input_ext = raw_input(question6 + options6).strip()
	input_ext = '*' + input_ext

# if a settings file does not exist, write one
if not settings_exists:
# 	Save the settings to be used for future runs
	settings_file = "settings.py"
	f = open(settings_file, "w")

#	 Fix the structure settings for the next run (if it changed)
	initial_structure_s = final_structure

	settings = """#!/usr/bin/env python2.7
''' question1 = {question1}
options1 = {options1}'''
task = {task}



''' question2 = {question2}
options2 = {options2}'''
initial_structure = {initial_structure_s}


''' question3 = {question3}
options3 = {options3}'''
final_structure = {final_structure}


''' question4 = {question4}
options4 = {options4}'''
input_code = {input_code}
automatic_code_type = {automatic_code_type}


''' question5 = {question5}
options5 = {options5}'''
hpc_load = {hpc_load}
cycle_pause = {cycle_pause}


''' question6 = {question6}
options6 = {options6}'''
input_ext = '{input_ext}'
"""
	settings = settings.format(**locals())
	f.write(settings)
	f.close()

## Begin actual work
# Get the input names 
input_names = []
cut = len(input_ext)
input_prefix = []
remove_file('*.out')
output_ext = ".out"

if initial_structure is 2:
	initial_dirs = next(os.walk('.'))[1]
	print '\nThese are the initial directories: ', initial_dirs
	used_dirs = list(initial_dirs)
	for i, dir_name in enumerate(initial_dirs):
		os.chdir(dir_name)
		input_name = glob.glob(input_ext)
		if not input_name:
			print "No input was found in: " + dir_name
			used_dirs.remove(dir_name)
			os.chdir('..')
			continue
		input_names += input_name
		os.chdir('..')
	initial_dirs = list(used_dirs)
	print '\nInputs were found in these directories: ', initial_dirs
	for input_name in input_names:
#		input_prefix.append(input_name.strip(input_ext.strip('*')))
		input_prefix.append(get_prefix(input_name, input_ext))
	print 'Input names are:', input_names	
	print 'Input prefixes are:', input_prefix	
else:
	cycle = 1
	found_input = False

	input_names = glob.glob(input_ext)
	if not input_names:
		print "No input files found with extension " + input_ext
		print "Exiting!"
		quit()
	for input_name in input_names:
#		input_prefix.append(input_name.strip(input_ext.strip('*')))
		input_prefix.append(get_prefix(input_name, input_ext))

	print '\nInput names are:', input_names	
	print 'Input prefixes are:', input_prefix
	for i in range(len(input_prefix)):
		os.mkdir(input_prefix[i])
		move = 'mv ' + input_names[i] + ' ' + input_prefix[i]
		os.system(move)
	initial_dirs = input_prefix

# Check to see if an input names were actually pulled
# I think this is outdated by the new method
if bool(input_names) is False:
	print "\n\nNo files with the extension", input_ext.strip('*'), "were found!"
	print "Exiting the program!"
	quit()
else:
	for i in range(len(input_names)):
		value = bool(input_names[i])
		if value is False:
			print "The program pulled an empty string for the input name! (might be broken)"
			print "Exiting!"
			quit()
# Run the cases
# first sort the names so they run in order, check to make sure they all sort the same
sort = True
sort_dir = sorted(initial_dirs)
sort_prefix = sorted(input_prefix)
sort_input_names = sorted(input_names)
for i in range(len(initial_dirs)):
	if initial_dirs[i] != input_prefix[i]:
		sort = False
	elif sort_dir[i] != sort_prefix[i]:
		sort = False
for i, sorted_input_name in enumerate(sort_input_names):
	if sorted_input_name.strip(input_ext.strip('*')) != sort_prefix[i]:
		sort = False
if sort is True:
	initial_dirs = sorted(initial_dirs)
	input_names = sorted(input_names)
	input_prefix = sorted(input_prefix)
else:
	print "\nSorting has been turned off because no correlation was determined\n"
 
cycle = 1
job_id = []
for i in range(len(initial_dirs)):
#       write the job submission scripts to each directory
	os.chdir(initial_dirs[i])
	job_name = input_prefix[i] + '.sh'
	remove_file('*.out')
	remove_file('*.sh*')
	remove_file('results.csv')

	if automatic_code_type:
		input_code = get_code_type(input_names[i])
		if input_code == "UNKNOWN":
			print "\nCode type could not be determined, skipping input file: " + input_names[i]
			continue

	if input_code == 1:
		job_sub = write_scale_sub(input_prefix[i], input_names[i], task, final_structure)
	else:
		job_sub = write_mcnp_sub(input_prefix[i], input_names[i], task, final_structure)

	with open(job_name, 'w') as s:
		s.write(job_sub)

#       make the job submission script executable and submit the job to the cluster
	print '\n\nSubmitting:', input_prefix[i]
	os.chmod(job_name, 0777)
	cmd = ['msub', job_name]
	run_job = (subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]).strip('\n')
	job_id.append([initial_dirs[i], run_job, job_name])
	print "Job ID:    ", job_id[i][1]
	print "Code type: ", get_code_type(input_names[i])	
	os.chdir('..')

# make sure to only use one node at a time to avoid clogging the cluster
	if cycle%cycle_pause == 0:
		print "\nLong/large submit limit has been reached, stopping at cycle ", cycle, "\n"
		check_job(job_id)
		print "\nJob submission is continuing\n" 
	cycle += 1

if task is 1:
	print '''\nJobs have been submitted (hopefully).'''
	quit()

# check the status of the jobs to see if they are still running
print "\n|---------------------------------------------|"
print "| Job status will be checked every 10 seconds |"
print "|---------------------------------------------|\n"

check_job(job_id)
	
print "|-------------------------|"
print "| All jobs have finished! |"
print "|-------------------------|\n"

# write results to "final.csv": columns are [input_name keff error keff+2error]: other math operations/data manipulation can easily be included here
time.sleep(1)
#os.system("rm final.csv 2>~/"+rm_err_file)
remove_file('final.csv')
for i in range(len(initial_dirs)):
	os.chdir(initial_dirs[i])
#	os.system('rm *.sh.o* 2>~/'+rm_err_file)
	os.system("cat results.csv >> ../final.csv") 
	os.chdir("..")

if final_structure is 1:
	for i in range(len(initial_dirs)):
		os.chdir(initial_dirs[i])
		move_inp = 'mv ' + input_names[i] + ' ..'
		move_out = 'mv *' + output_ext + ' ..'
		os.system(move_inp)	
		os.system(move_out)
		os.chdir('..')
		rm_dir = 'rm -r ' + initial_dirs[i]
		os.system(rm_dir)

# Check the final.csv file for error messages
print ""
final = []
with open('final.csv') as f:
	for line in f:
		row = line.split()
		final.append(row)
for i in range(len(final)):
	if 'ERROR' in final[i]:
		print '\033[1m'+'!!!WARNING!!! '+'\033[0m'+'There is an error with case', final[i][0]+' please check the input/output and try again'
print "\n\nFinished!"
print "Results are printed in the final.csv file"
if input_code is 1:
	print "The final.csv columns for SCALE are: Input, keff, "+u"\u03C3"+", keff+2"+ u"\u03C3"+", ealf, ealf error, X^2 check\n"
else:
	print "The final.csv columns for MCNP are: Input, keff, "+u"\u03C3"+", keff+2"+u"\u03C3"+", ealf, source entropy convergence check, X^2 check\n"
