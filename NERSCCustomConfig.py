import os

# change the defaults if you want

def CustomConfig(run, balrog, DESdb, db, tiles, where):

    '''
    # Always check these
    run['label'] = 'ndbg'
    run['joblabel'] = 'test'
    run['ppn'] = 8
    run['nodes'] = 2
    run['walltime'] = '24:00:00'
    run['queue'] = 'regular'
    tiles = tiles[30:32]


    # If you're not debugging these should be pretty stable not to need to change. 100,000 for the tiletotal gets you to about observed DES number density.
    # Warning: if you make the cleaning parameters False you will use LOTS of disk space
    run['tiletotal'] = 5000
    run['DBoverwrite'] = True
    run['command'] = 'system'
    run['DBload'] = 'cx_Oracle'
    run['inc'] = 100
    run['outdir'] = os.path.join(os.environ['SCRATCH'], 'BalrogScratch')
    run['intermediate-clean'] = True
    run['tile-clean'] = True
    run['bands'] = ['g', 'r', 'i', 'z', 'Y']
    run['dualdetection'] = [1,2,3]
    balrog['oldmorph'] = True


    if balrog['oldmorph']:
        balrog["reff"] = "HALF_LIGHT_RADIUS"
        balrog["sersicindex"] = "SERSIC_INDEX"
    '''

    run['label'] = 'ndbg3'
    run['joblabel'] = 'test'
    run['ppn'] = 8
    run['nodes'] = 1
    tiles = tiles[30:31]

    run['tiletotal'] = 3000
    run['DBoverwrite'] = True
    run['command'] = 'popen'
    run['DBload'] = 'cx_Oracle'
    run['inc'] = 100
    run['outdir'] = os.path.join(os.environ['SCRATCH'], 'BalrogScratch')
    run['intermediate-clean'] = True
    run['tile-clean'] = True
    run['bands'] = ['i']
    run['dualdetection'] = None
    balrog['oldmorph'] = True


    if balrog['oldmorph']:
        balrog["reff"] = "HALF_LIGHT_RADIUS"
        balrog["sersicindex"] = "SERSIC_INDEX"


    return run, balrog, DESdb, db, tiles
