#! /usr/bin/python

import os
import sys
import optparse
import inotify.adapters
import subprocess
import shutil

# retrieve list of directories from the arguments
# and add them to the watch list
i = inotify.adapters.Inotify()
p = optparse.OptionParser()
(options, arguments) = p.parse_args()
if arguments == []:
    arguments = [os.getcwd()]

for d in arguments:
    if not os.path.isdir(d):
        print repr(d) + " is not a valid directory"
    print "watching:", d
    i.add_watch(os.path.abspath(d))

last_seen = {} # use this to keep a record of the last time
               # a file was worked on
for event in i.event_gen():
    if event is None:
        continue

    (header, type_names, watch_path, filename) = event

    #short circuits
    if not "IN_MODIFY" in type_names:
        continue
    if not filename.endswith(".java"):
        continue

    # build all variables to be used later
    source_file = os.path.abspath(
                            os.path.join(watch_path, filename))
    webapp = source_file.split(os.sep)
    index = webapp.index("src")
    webapp = webapp[index-1]
    reload_url = "http://10.4.0.1:8080/manager/text/reload?path=/" +\
                 webapp
    compiled_file = source_file.rstrip(".java") + ".class"
    dest_file = compiled_file.replace("/src/", "/WEB-INF/classes/")

    # try and only compile a file once
    # assume any file with mtimes less than 0.5sec apart
    # is the same 'save' action
    try:
        if last_seen[source_file] + 0.5 > \
                os.path.getmtime(source_file):
            continue
    except KeyError:
        pass
    last_seen[source_file] = os.path.getmtime(source_file)

    # call the compile, move, reload commands
    print source_file,
    print "compiling...",
    sys.stdout.flush()
    rval = subprocess.call("javac " + source_file, shell=True)
    if rval != 0:
        print
        print "encountered compile error"
        continue
    print "moving...",
    sys.stdout.flush()
    try:
        shutil.move(compiled_file, dest_file)
    except: # move isn't erroring right now. It is actually
            # overwriting files it shouldn't be able to
            # overwrite right now
        print
        print "encountered error while moving class"
        continue
    print "reload", webapp + "...",
    sys.stdout.flush()
    rval = subprocess.call("wget " + reload_url +
                    " --quiet -O /dev/null" +
                    " --user=admin-script --password=admin3#",
                    shell=True)
    if rval != 0:
        print
        print "encountered an error while reloading the webapp"
        continue
    print "done."
