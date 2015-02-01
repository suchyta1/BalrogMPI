
Installation requirements:

* I slightly hacked desdb to get an extra function that wasn't callable. Add this line to the try block in desdb/__init__.py:
    from .desdb import get_tabledef
* add this directory to your enviorment variables as BALROG_MPI


Some quick notes about some of the files:
* job-debug is the queue submit file for wq (queue installed at BNL)
* RunConfigurations.py sets up things you want to do in your run
* WrapBalrog.py reads RunConfiguations.py and does all the MPI stuff
* runbalrog.py runs the balrog realizations on a node
* mpifunctions.py has some functions I wrote to make life easier working with MPI4py
