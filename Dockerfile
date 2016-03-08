FROM debian:7.9
MAINTAINER Eric Suchyta <eric.d.suchyta@gmail.com>

ENV valarauko /Valarauko-job
RUN  apt-get update && apt-get install -y wget libaio-dev python-dev python-numpy libfftw3-dev libboost-all-dev libblas-dev g++ scons git make python-pip libatlas-base-dev && \
	pip install --no-deps astropy fitsio esutil && \
	mkdir /software && cd /software && wget http://www.cosmo.bnl.gov/www/esheldon/code/misc/des-oracle-linux-x86-64-v2.tar.gz && \
	tar xvzf des-oracle-linux-x86-64-v2.tar.gz && rm des-oracle-linux-x86-64-v2.tar.gz && cd des-oracle-linux-x86-64-v2 && ./do-install /software/des-oracle-linux-x86-64-v2/install && \
	rm -r instantclient_11_2/ && rm -r cx_Oracle-5.1.1-ess/ && rm cx_Oracle-5.1.1-ess.tar.gz && \
	cd /software && git clone https://github.com/esheldon/desdb.git && cd desdb/ && python setup.py install && cd /software && rm -r desdb/ && \
	cd /software && git clone https://github.com/suchyta1/suchyta_utils.git && cd suchyta_utils && python setup.py install && cd /software && rm -r suchyta_utils && \
	git clone https://github.com/emhuff/Balrog.git && cd Balrog/ && rm -r default_example/ && rm -r astro_config/ && rm cosmos* && yes | rm -r .git/ && \
	cd /software && git clone https://github.com/suchyta1/Valarauko.git && \


	mkdir tmv && wget https://googledrive.com/host/0B6hIz9tCW5iZdEcybFNjRHFmOEE/tmv0.72.tar.gz && tar xvzf tmv0.72.tar.gz && rm tmv0.72.tar.gz && \
	cd tmv0.72 && scons install PREFIX=/software/tmv && cd /software && rm -r tmv0.72 && \
	git clone https://github.com/GalSim-developers/GalSim.git && cd GalSim && scons TMV_DIR=/software/tmv && scons install  && cd /software && rm -r GalSim/ && \

	wget --no-check-certificate 'https://googledrive.com/host/0B4AAwvZlUdfeT2V0ZTVhTlFDc1E' -O swarp-2.36.2.tar.gz && tar xvzf swarp-2.36.2.tar.gz && rm swarp-2.36.2.tar.gz && \
	cd swarp-2.36.2/ && ./configure && make && make install && cd /software && rm -r swarp-2.36.2/ && \
	wget --no-check-certificate 'https://googledrive.com/host/0B4AAwvZlUdfeeURxS3RsZWw5VDg' -O sextractor-2.18.10.tar.gz && tar xvzf sextractor-2.18.10.tar.gz && rm sextractor-2.18.10.tar.gz && \
	cd sextractor-2.18.10/ && ./configure --with-atlas-incdir=/usr/include/atlas && make && make install && cd /software && rm -r sextractor-2.18.10/ && \
	wget --no-check-certificate 'https://googledrive.com/host/0B4AAwvZlUdfeOV9QQmxGNmlrcUE' -O cfitsio-3.360.tar.gz && tar xvzf cfitsio-3.360.tar.gz && rm cfitsio-3.360.tar.gz && \
	cd cfitsio && ./configure && make && make install && make funpack && cp funpack /usr/bin && cd /software && rm -r cfitsio && \

	apt-get --purge autoremove -y libblas-dev g++ scons git make python-pip libatlas-base-dev && apt-get -y clean && \

	mkdir $valarauko && mkdir $valarauko/jobroot && mkdir $valarauko/outroot && mkdir $valarauko/slrroot && mkdir $valarauko/catroot && mkdir $valarauko/posroot && \
	mkdir /home/user && mkdir /home/user/site && \
	echo 'if [ -f ~/.bashrc ]; then source ~/.bashrc; fi' >> ~/.bash_profile && \
	echo 'export PYTHONPATH' >> /software/des-oracle-linux-x86-64-v2/install/setup.sh && \
	echo 'source /software/des-oracle-linux-x86-64-v2/install/setup.sh' >> ~/.bashrc && \
	echo 'export PYTHONPATH=/software/Balrog:${PYTHONPATH}' >> ~/.bashrc && \
	echo 'export DESREMOTE=https://desar2.cosmology.illinois.edu:/DESFiles/desardata' >> ~/.bashrc && \
	echo 'export DESPROJ=OPS' >> ~/.bashrc && \
	echo 'export HOME=/home/user/site' >> ~/.bashrc && \
	cp /root/.bashrc /home/user/.bashrc && chmod 755 /home/user/.bashrc && \
	cp /root/.bash_profile /home/user/.bash_profile && chmod 755 /home/user/.bash_profile


# Don't need to use these. This version of TMV was built by me and then reused to save build time when testing.
#mv /bin/sh /bin/sh.orig && ln -s /bin/bash /bin/sh && \
#wget https://googledrive.com/host/0B4AAwvZlUdfeWFNiN1RLZUpVOU0 -O tmv-0.72-debian.tar.gz && tar xvzf tmv-0.72-debian.tar.gz && rm tmv-0.72-debian.tar.gz && \
#git clone https://github.com/GalSim-developers/GalSim.git && cd GalSim && scons TMV_DIR=/software/tmv-0.72-debian && scons install && cd /software && rm -r GalSim/ && \
