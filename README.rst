=============
ISPYB MONITOR
=============

This plugin contains a monitor to send data to an ISPyB database, so having a working ISPyB database is required.
Below we summarize the steps taken to test this plugin if you don't already have ISPyB.

=====
Setup
=====

- **Install MariaDB**: Download choosing OS and version (recommended >=10.2), follow steps: https://downloads.mariadb.org/mariadb/repositories/#mirror=digitalocean-sfo&distro=Ubuntu&distro_release=xenial--ubuntu_xenial&version=10.3

- **Fix root login**: check if you can log in as root to mysql ( ``$mysql -u root -p`` ).Skip this step if you log in successfully.If not, use the accepted answer on this link to fix your root login: https://askubuntu.com/questions/705458/ubuntu-15-10-mysql-error-1524-unix-socket.

- **Log in as root**:

.. code-block::

    $mysql -u root -p

- **Set log_bin_trust_function_creators**:

.. code-block::

    MariaDB [(none)]> set global log_bin_trust_function_creators=ON;
    Query OK, 0 rows affected (0.000 sec)


- **Create DB**:

.. code-block::

    MariaDB [(none)]> create database ispyb;
    Query OK, 1 row affected (0.000 sec)

- **Create user for DB**: Grant privileges to your user on ispyb database we just created. See https://stackoverflow.com/questions/5016505/grant-all-privileges-on-database . Here we create a user username that can log in without password.

.. code-block::

    MariaDB [(none)]> CREATE USER username;
    MariaDB [(none)]> CREATE USER username@’localhost’;
    MariaDB [(none)]> use ispyb
    MariaDB [(ispyb)]> GRANT ALL PRIVILEGES ON ispyb.* to username@'localhost';
    MariaDB [(ispyb)]> grant all privileges on ispyb.* to username@'%';

- **Add schemas**: Clone this repository and follow steps to add schemas https://github.com/DiamondLightSource/ispyb-database

- **Create a config file**: based on https://github.com/DiamondLightSource/ispyb-api/blob/master/conf/config.example.cfg

.. code-block::

    [ispyb_mysql_sp]
    user = username
    pw =
    host = localhost
    port = 3306
    db = ispyb

- **Set ISPYB_CONFIG**: you can do it in the terminal where you will launch Scipion doing ``export ISPYB_CONFIG=path/to/ispyb.cfg`` or set it in the variables section of ~/.config/scipion/scipion.conf)

.. code-block::

    [VARIABLES]
    SCIPION_NOTES_PROGRAM =
    SCIPION_NOTES_ARGS =
    SCIPION_NOTES_FILE = notes.txt
    SCIPION_NOTIFY = False
    ISPYB_CONFIG=/path/to/ispyb.conf

- **Install this plugin:**

.. code-block::

    scipion installp -p scipion-em-ispyb

Alternatively, in devel mode:

.. code-block::

    scipion installp -p local/path/to/scipion-em-ispyb --devel


============
Run and test
============

- **Run Scipion and the ISPyB monitor**: you should now be able to find the ISPyB monitor in the list of available protocols of Scipion. Launch a workflow with one or all of the following protocols: import movies,movie  alignment, ctf estimation (TestStreamingWorkflow is a good candidate), and set them as the input of ISPyB Monitor. For test purposes, you can select "test" as the database in the dropdown menu at the bottom, and use **cm14451-2** as the visit.

- **ISPyB import error**: If the monitor fails because it can’t import bz2, we need to install in our system libbz2-dev and re-install Scipion:

.. code-block::

    sudo apt-get install libbz2-dev
    rm -rf software/lib/*
    rm -rf software/include/*
    rm software/bin/*
    scipion install -j 8

- **Check the data in the ISPyB database**:

.. code-block::

    MariaDB [ispyb]> select micrographFullPath, movieId, totalMotion from MotionCorrection;
    +--------------------------------------------------------------+---------+-------------+
    | micrographFullPath                                           | movieId | totalMotion |
    +--------------------------------------------------------------+---------+-------------+
    | Runs/000615_ProtMotionCorr/extra/movie000001_aligned_mic.mrc |       1 |     1.96068 |
    | Runs/000615_ProtMotionCorr/extra/movie000002_aligned_mic.mrc |       2 |     3.57892 |
    | Runs/000615_ProtMotionCorr/extra/movie000003_aligned_mic.mrc |       3 |     2.17066 |
    | Runs/000615_ProtMotionCorr/extra/movie000004_aligned_mic.mrc |       4 |     1.96068 |
    | Runs/000615_ProtMotionCorr/extra/movie000005_aligned_mic.mrc |       5 |     3.57892 |
    | Runs/000615_ProtMotionCorr/extra/movie000006_aligned_mic.mrc |       6 |     2.17066 |
    | Runs/000615_ProtMotionCorr/extra/movie000007_aligned_mic.mrc |       7 |     1.96068 |
    | Runs/000615_ProtMotionCorr/extra/movie000008_aligned_mic.mrc |       8 |     3.57892 |
    | Runs/000615_ProtMotionCorr/extra/movie000009_aligned_mic.mrc |       9 |     2.17066 |


