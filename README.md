Artist Community Website
------------------------

This is a website built for artists to upload their paintings. An artist
can use their facebook or google account to log in. They can add artists
(typically themselves) and their paintings.Other artists can leave
comments/feedback on the paintings. An artist may delete or modify
artists or paintings they have created. He/she may also delete
comments on his/her paintings.

Requirements:
-------------

The following must be installed on your machine:
Python
VM and vagrant
sqlite

Download:
---------

Go to this website https://github.com/anudhagat/artist-community.
Click on the Download Zip button. This will copy a zipped version onto your
local computer. Unzip the files.

Setup Database:
---------------

To setup the artists.db sqlite database, run this command from the shell:
python database_setup.py

To populate the database with some data for testing, run this command from the shell:
python somedata.py

Run webserver:
--------------
To startup the website, run the project.py file using this command form the shell:
python project.py

This webserver listens in on port 5000.

For testing, my client (web browser) was on the same machine as my webserver.
I tested the functionality of project.py by opening up the web browser (chrome) and
typing localhost:5000 in the url.
