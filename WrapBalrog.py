#!/usr/bin/env python

import sys
import os
import Queue
import numpy as np
import desdb
import copy
import pywcs
import pyfits

import itertools
from mpi4py import MPI
import mpifunctions

from RunConfigurations import *
import runbalrog



def SendEmail(config):
    import smtplib
    from email.mime.text import MIMEText
    
    sender = 'eric.d.suchyta@gmail.com'
    receivers = [sender]
    msg = MIMEText( "Balrog run %s finished. \n \n--Message automatically generated by Balrog." %(config['label']) )
    msg['Subject'] = '%s completed' %(config['label'])
    msg['From'] = sender
    msg['To'] = sender
    
    '''
    sender = 'eric.d.suchyta@gmail.com'
    receivers = [sender]
    message = """From: Eric Suchyta <eric.d.suchyta@gmail.com>
    To: Eric Suchyta <eric.d.suchyta@gmail.com>
    Subject: %s completed

    Balrog run %s finished.
    """ %(config['label'], config['label'])
    '''

    obj = smtplib.SMTP('localhost')
    obj.sendmail(sender, receivers, msg.as_string())



def GetFiles(RunConfig, SheldonConfig, tiles):
    bands = RunConfig['bands']
    runs = np.array( desdb.files.get_release_runs(SheldonConfig['release'], withbands=bands) )
    if RunConfig['dualdetection']:
        bands.insert(0, 'det')
    kwargs = {}
    kwargs['type'] = SheldonConfig['filetype']
    kwargs['fs'] = 'net'

    keepruns = []
    keepimages = []
    keeppsfs = []

    for i in range(len(runs)):
        run = runs[i]
        tile = run[-12:]
        if tile in tiles:
            keepruns.append(run)
            keepimages.append( [] )
            keeppsfs.append( [] )
            kwargs[SheldonConfig['runkey']] = run
            kwargs['tilename'] = tile

            for band in RunConfig['bands']:
                kwargs['band'] = band
                image = desdb.files.get_url(**kwargs)
                image = image.replace('7443','')
                psf = image.replace('.fits.fz', '.psfcat.psf')
                keepimages[-1].append(image)
                keeppsfs[-1].append(image)

    return [keepimages, keeppsfs]    


def RandomPositions(RunConfiguration, BalrogConfiguration, tiles, seed=None):
    cur = desdb.connect()
    q = "select urall, uraur, udecll, udecur, tilename from coaddtile"
    all = cur.quick(q, array=True)
    cut = np.in1d(all['tilename'], tiles)
    dcoords = all[cut]
    ramin = np.amin(dcoords['urall'])
    ramax = np.amax(dcoords['uraur'])
    decmin = np.amin(dcoords['udecll'])
    decmax = np.amax(dcoords['udecur'])


    if decmin < 0:
        decmin = 90 - decmin
    if decmax < 0:
        decmax = 90 - decmax


    wcoords = []
    for tile in tiles:
        wcoords.append( np.empty( (0,2) ) )

    target = len(tiles) * RunConfiguration['tiletotal'] / float(MPI.COMM_WORLD.size)
    #inc = 10000 
    inc = 1
    
    if seed!=None:
        np.random.seed(seed)

    numfound = 0
    while numfound < target:
        ra = np.random.uniform(ramin,ramax, inc)
        dec = np.arccos( np.random.uniform(np.cos(np.radians(decmin)),np.cos(np.radians(decmax)), inc) ) * 180.0 / np.pi
        neg = (dec > 90.0)
        dec[neg] = 90.0 - dec[neg]
        coords = np.dstack((ra,dec))[0]
    
        for i in range(len(tiles)):

            tilecut = (dcoords['tilename']==tiles[i])
            c = dcoords[tilecut][0]
            inside = (ra > c['urall']) & (ra < c['uraur']) & (dec > c['udecll']) & (dec < c['udecur'])
          
            found = np.sum(inside)
            if found > 0:
                wcoords[i] = np.concatenate( (wcoords[i],coords[inside]), axis=0)
            numfound += found

    #wcoords = np.array(wcoords)
    for i in range(len(wcoords)):
        wcoords[i] = mpifunctions.Gather(wcoords[i])
    return wcoords


def DropTablesIfNeeded(RunConfig, BalrogConfig):
    cur = desdb.connect()
    user = cur.username

    tables = ['truth', 'sim']
    try:
        tmp = BalrogConfig['nonosim']
    except:
        tables.insert(1, 'nosim')
    if RunConfig['doDES']:
        tables.append('des')

    bands = RunConfig['bands']
    if RunConfig['dualdetection']:
        bands.insert(0, 'det')

    for table in tables:
        for band in bands:
            t = '%s.balrog_%s_%s_%s' %(user, RunConfig['label'], table, band)
            cur.quick("BEGIN \
                            EXECUTE IMMEDIATE 'DROP TABLE %s'; \
                        EXCEPTION \
                            WHEN OTHERS THEN \
                                IF SQLCODE != -942 THEN \
                                    RAISE; \
                                END IF; \
                        END;" %(t))
    return tables


def PrepareCreateOnly(tiles, images, psfs, position, config):
    return tiles[0:1], images[0:1], psfs[0:1], [ [] ], [-2]


def PrepareIterations(tiles, images, psfs, position, config, RunConfig):
    sendpos = copy.copy(position)
    senditerations = []

    for i in range(len(tiles)):
        iterations = np.ceil( len(pos[i]) / float(config['ngal']))
        sendpos[i] = np.array_split(pos[i], iterations, axis=0)
        if RunConfig['doDES']:
            senditerations.append(np.arange(-1, iterations, 1, dtype=np.int32))
            sendpos[i].insert(0, [])
        else:
            senditerations.append(np.arange(0, iterations, 1, dtype=np.int32))


    return tiles, images, psfs, sendpos, senditerations



if __name__ == "__main__":
    RunConfig = RunConfigurations.default
    SheldonConfig = desdbInfo.sva1_coadd
    tiles = TileLists.suchyta13[1:3]
    config = BalrogConfigurations.default

    pos = RandomPositions(RunConfig, config, tiles)

    if MPI.COMM_WORLD.Get_rank()==0:
        images, psfs = GetFiles(RunConfig, SheldonConfig, tiles)
        tables = DropTablesIfNeeded(RunConfig, config)


    """This will do the minimal Balrog runs, which only run so the outputs exist to know what needs to write to the DB.
    RunBalrog is in runbalrog.py, and does the work
    """
    if MPI.COMM_WORLD.Get_rank()==0:
        sendtiles, sendimages, sendpsfs, sendpos, senditerations = PrepareCreateOnly(tiles, images, psfs, pos, config)
    else:
        sendtiles = sendimages = sendpsfs = sendpos = senditerations = None
    sendpos, sendtiles, sendimages, sendpsfs, senditerations = mpifunctions.Scatter(sendpos, sendtiles, sendimages, sendpsfs, senditerations)
    for i in range(len(senditerations)):
        #print 'sendpos =', sendpos
        #print 'sendtiles[%i] ='%i, sendtiles[i]
        #print 'sendimages[%i] ='%i, sendimages[i]
        #print 'sendpsfs[%i] ='%i, sendpsfs[i]
        #print 'senditerations[%i] ='%i, senditerations[i]
        runbalrog.NewRunBalrog( sendpos, sendtiles[i], sendimages[i], sendpsfs[i], senditerations[i], RunConfig, config)


    '''
    """This is all the real Balrog realizations. Everything not passed to RunBalrog should be easily parseable from the config dictionaries, *I think*
    RunBalrog is in runbalrog.py, and does the work
    """
    if MPI.COMM_WORLD.Get_rank()==0:
        sendtiles, sendimages, sendpsfs, sendpos, senditerations = PrepareIterations(tiles, images, psfs, pos, config, RunConfig)
    else:
        sendtiles = sendimages = sendpsfs = sendpos = senditerations =  None
    sendpos, sendtiles, sendimages, sendpsfs, senditerations = mpifunctions.Scatter(sendpos, sendtiles, sendimages, sendpsfs, senditerations)
    for i in range(len(senditerations)):
        #if MPI.COMM_WORLD.Get_rank()==0:
        #    print 'sendpos[%i] ='%i, sendpos[i]
        #    print 'sendtiles[%i] ='%i, sendtiles[i]
        #    print 'sendimages[%i] ='%i, sendimages[i]
        #    print 'sendpsfs[%i] ='%i, sendpsfs[i]
        #    print 'senditerations[%i] ='%i, senditerations[i]
        runbalrog.NewRunBalrog( sendpos[i], sendtiles[i], sendimages[i], sendpsfs[i], senditerations[i], RunConfig, config)
    '''

    """
    if MPI.COMM_WORLD.Get_rank()==0:
        SendEmail(config)
    """
