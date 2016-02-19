#!/usr/bin/env python

import sys
import os
import numpy as np
import desdb
import copy
import socket
import logging
import json
import multiprocessing
import shutil
import esutil

import RunBalrog as runbalrog
import balrog as balrogmodule


def SendEmail(config, file):
    if config['email'] is None:
        return

    import smtplib
    from email.mime.text import MIMEText
    
    sender = config['email']
    receivers = [sender]
    msg = MIMEText( "Balrog configured in %s finished. \n \n--Message automatically generated by Balrog." %(file) )
    msg['Subject'] = '%s completed' %(config['dbname'])
    msg['From'] = sender
    msg['To'] = sender
    
    obj = smtplib.SMTP('localhost')
    obj.sendmail(sender, receivers, msg.as_string())


def GetFiles2(config):
    tiles = np.array(config['tiles'], dtype='|S12')
    df = desdb.files.DESFiles(fs='net')
    bands = runbalrog.PrependDet(config['run'])
    conn = desdb.connect()

    images = []
    psfs = []
    bs = []
    skipped = []
    usetiles = []

    for i in range(len(tiles)):
        for j in range(len(bands)):

            band = bands[j]

            if band=='det':
                d = conn.quick("SELECT c.run from coadd c, runtag rt where rt.run=c.run and c.tilename='%s' and rt.tag='%s' and c.band is null" %(tiles[i], config['run']['release'].upper()), array=True )
            else:
                d = conn.quick("SELECT c.run from coadd c, runtag rt where rt.run=c.run and c.tilename='%s' and rt.tag='%s' and c.band='%s'" %(tiles[i], config['run']['release'].upper(), band), array=True )
           
            if len(d)==0:
                if band=='det':
                    skipped.append(tiles[i])
                    break
                else:
                    continue

            if j==0:
                usetiles.append(tiles[i])
                psfs.append([])
                images.append([])
                bs.append([])

            run = d[0]['run']
            img = df.url('coadd_image', coadd_run=run, tilename=tiles[i], band=band)
            images[-1].append(img)
            psfs[-1].append(img.replace('.fits.fz', '_psfcat.psf'))
            bs[-1].append(band)

    return [images, psfs, usetiles, bs, skipped]
            

def GetAllBands():
    return ['det','g','r','i','z','Y']


# Delete the existing DB tables for your run if the names already exist
def DropTablesIfNeeded(RunConfig, indexstart, size, tiles):
    allbands = GetAllBands()
    cur = desdb.connect()
    user = cur.username
    write = True

    arr = cur.quick("select table_name from dba_tables where owner='%s'" %(user.upper()), array=True)
    tables = arr['table_name']

    for  kind in ['truth', 'nosim', 'sim', 'des']:
        tab = 'balrog_%s_%s' %(RunConfig['dbname'], kind)

        if (tab.upper() in tables):
            if RunConfig['DBoverwrite']:
                cur.quick("DROP TABLE %s PURGE" %tab)
            else:
                write = False
                if (kind=='truth') and RunConfig['verifyindex']:
                    for i in range(len(tiles)):
                        arr = cur.quick("select balrog_index from %s where tilename='%s'"%(tab,tiles[i]), array=True)
                        this = np.arange(indexstart[i], indexstart[i]+size[i], 1)
                        inboth = np.in1d(np.int64(this), np.int64(arr['balrog_index']))
                        if np.sum(inboth) > 0:
                            raise Exception("You are trying to add balrog_index(es) which already exist. Setting verifyindex=False is the only way to allow this. But unless you understand what you're doing, and have thought of reasons I haven't, don't duplicate balrog_index")

    return write


def InitCommonToTile(tile,images,psfs,indexstart,bands, config):
        derived = {'images': images,
                   'psfs': psfs,
                   'indexstart': indexstart,
                   'db': config['db'],
                   'imbands': bands}
        if config['run']['fixwrapseed'] != None:
            derived['seedoffset'] = RunConfig['fixwrapseed']
        else:
            derived['seedoffset'] = np.random.randint(10000)

        balrog = copy.copy(config['balrog'])
        balrog['tile'] = tile

        return derived, balrog

def TileIterations(tile,images,psfs,indexstart,bands,pos, config, write):
    derived, balrog = InitCommonToTile(tile,images,psfs,indexstart,bands, config)

    workingdir = os.path.join(config['run']['outdir'], balrog['tile'] )
    derived['workingdir'] = workingdir
    derived['indir'] = os.path.join(workingdir, 'input')
    runbalrog.Mkdir(derived['indir'])

    iterations = len(pos) / balrog['ngal']
    if ( len(pos) % balrog['ngal'] ) != 0:
        iterations += 1

    itQ = []
    posQ = []

    if write:
        itQ.append(-2)
        posQ.append(None)

    '''
    if RunConfig['doDES']:
        for k in range(len(band)):
            itQ.append( (-1, k) )
            posQ.append(None)
    '''

    for j in range(int(iterations)):
        start = j * balrog['ngal']
        if j==(iterations-1):
            stop = len(pos)
        else:
            stop = start + balrog['ngal']
        itQ.append(j)
        posQ.append(pos[start:stop])

    return derived, balrog, posQ, itQ


def GetPos(RunConfig, tiles):
    pos = []
    ind = []
    size = []
    for tile in tiles:
        f = os.path.join(RunConfig['pos'], '%s.fits'%(tile))
        data, header = esutil.io.read(f, header=True)
        indexstart = header['istart']
        ind.append(indexstart)

        if RunConfig['downsample'] is None:
            s = len(data)
        else:
            s = RunConfig['downsample']
        size.append(s)

        d = np.zeros( (s,2) ) 
        d[:, 0] = data['ra'][0:s]
        d[:, 1] = data['dec'][0:s]
        pos.append(d)
    return pos, ind, size


def run_balrog(args):
    RunConfig, BalrogConfig, DerivedConfig = args
    it = runbalrog.EnsureInt(DerivedConfig)

    host = socket.gethostname()
    ild = os.path.join(DerivedConfig['itlogdir'], BalrogConfig['tile'])
    DerivedConfig['itlogfile'] = os.path.join(ild, '%i.log'%it)
    if RunConfig['command']=='popen':
        DerivedConfig['itlog'] = runbalrog.SetupLog(DerivedConfig['itlogfile'], host, '%s_%i'%(BalrogConfig['tile'],it))
    elif RunConfig['command']=='system':
        DerivedConfig['itlog'] = DerivedConfig['itlogfile']
    DerivedConfig['setup'] = balrogmodule.SystemCallSetup(retry=RunConfig['retry'], redirect=DerivedConfig['itlog'], kind=RunConfig['command'], useshell=RunConfig['useshell'])


    if it==-2:
        # Minimal Balrog run to create DB tables
        runbalrog.RunOnlyCreate(RunConfig, BalrogConfig, DerivedConfig)

    elif it==-1:
        # No simulated galaxies
        runbalrog.RunDoDES(RunConfig, BalrogConfig, DerivedConfig)
    else:
        # Actual Balrog realization
        runbalrog.RunNormal2(RunConfig, BalrogConfig, DerivedConfig)

    if RunConfig['intermediate-clean']:
        if it < 0:
            shutil.rmtree(BalrogConfig['outdir'])
        else:
            for band in DerivedConfig['bands']:
                dir = os.path.join(DerivedConfig['outdir'], band)
                shutil.rmtree(dir)


def Run_Balrog(tiles,images,psfs,indexstart,bands,pos, config, write, runlogdir):
    host = socket.gethostname()
    rfile = os.path.join(runlogdir, 'common.log')
    runlog = runbalrog.SetupLog(rfile, host, '%s-all'%(host))

    for i in range(len(tiles)):
        runlog.info('Setting up tile %s'%(tiles[i]))
        if (i==0) and write:
            dowrite = True
        else:
            dowrite = False
        Derived, Balrog, Pos, It = TileIterations(tiles[i],images[i],psfs[i],indexstart[i],bands[i],pos[i], config, dowrite)
        Derived['itlogdir'] = os.path.join(runlogdir, 'iterations')
        ild = os.path.join(Derived['itlogdir'], Balrog['tile'])
        runbalrog.Mkdir(ild)

        args = []

        if config['run']['ppn'] is not None:
            ppn = config['run']['ppn']
        else:
            ppn = multiprocessing.cpu_count()
        pool = multiprocessing.Pool(ppn)


        for j in range(len(It)):

            balrog = copy.copy(Balrog)
            derived = copy.copy(Derived)

            derived['iteration'] = It[j]
            it = runbalrog.EnsureInt(derived)
            derived['pos'] = Pos[j]
            derived['outdir'] = os.path.join(derived['workingdir'], 'output', '%i'%it)
            runbalrog.Mkdir(derived['outdir'])


            balrog['indexstart'] = derived['indexstart']
            if it > 0:
                balrog['indexstart'] += it*balrog['ngal']
                balrog['ngal'] = len(derived['pos'])
            balrog['seed'] = balrog['indexstart'] + derived['seedoffset']

            if (j==0):
                runlog.info('Downloading tile data for tile %s'%(tiles[i]))
                setup = balrogmodule.SystemCallSetup(retry=config['run']['retry'], redirect=runlog, kind=config['run']['command'], useshell=config['run']['useshell'])
                derived['images'], derived['psfs'] = runbalrog.DownloadImages(derived['indir'], derived['images'], derived['psfs'], config['run'], setup, skip=False)

                if (It[j]==-2):
                    derived['bands'] = GetAllBands()
                    runlog.info('Creating database %s'%(config['run']['dbname']))
                    run_balrog( [config['run'], balrog, derived] )
                else:
                    derived['bands'] = runbalrog.PrependDet(config['run'])
                    args.append( [config['run'], balrog, derived] )

            else:
                derived['images'], derived['psfs'] = runbalrog.DownloadImages(derived['indir'], derived['images'], derived['psfs'], config['run'], None, skip=True)
                derived['bands'] = runbalrog.PrependDet(config['run'])
                args.append( [config['run'], balrog, derived] )

        runlog.info('Doing all the Balrog iterations for tile %s'%(tiles[i]))
        runlog.info('Found %i iterations'%(len(args)))
        pool.map(run_balrog, args)
        runlog.info('Finished %i iterations'%(len(args)))
        
        dir = Derived['workingdir']
        if config['run']['tile-clean'] and os.path.exists(dir):
            shutil.rmtree(dir)
            runlog.info('removed %s' %(dir) )

    dir = config['run']['outdir']
    if config['run']['tile-clean'] and os.path.exists(dir):
        shutil.rmtree(dir)
        runlog.info('removed %s' %(dir) )


if __name__ == "__main__":
  
    with open(sys.argv[1]) as jsonfile:
        config = json.load(jsonfile)

    runlogdir = sys.argv[2]
    if os.path.exists(runlogdir):
        shutil.rmtree(runlogdir)
    os.makedirs(runlogdir)

    images, psfs, tiles, bands, skipped = GetFiles2(config)
    pos, indexstart, size = GetPos(config['run'], tiles)
    write = DropTablesIfNeeded(config['run'], indexstart, size, tiles)
    Run_Balrog(tiles,images,psfs,indexstart,bands,pos, config, write, runlogdir)


    # This should be a script at the end of the job
    """
    # Send email when the run finishes
    MPI.COMM_WORLD.barrier()
    if MPI.COMM_WORLD.Get_rank()==0:
        SendEmail(RunConfig, sys.argv[1])
    """


