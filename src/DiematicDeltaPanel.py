#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading,queue
import logging, logging.config
import DDModbus
import time,datetime,pytz
from enum import IntEnum
from Diematic import Diematic,DDREGISTER

#This class allow to read/write parameters to Diematic3 regulator with the helo of a RS485/TCPIP converter
#refresh of attributes From regulator is done roughly every minute
#update request to the regulator are done within 10 s and trigger a whole read refresh
class DiematicDeltaPanel(Diematic):
	def __init__(self,ip,port,regulatorAddress,interfaceAddress,boilerTimezone='',syncTime=False):
		
		super().__init__(ip,port,0,interfaceAddress,boilerTimezone,syncTime)
        


#modbus loop, shall run in a specific thread. Allow to exchange register values with the Dielatic regulator
	def loop(self):
		#parameter validity duration in seconds after expiration of period
		#after this timeout, interface is reset
		VALIDITY_TIME=30
		try:
			self.run=True;
			#reset timeout
			self.lastSynchroTimestamp=time.time();
			while self.run:
				#wait for a frame received
				frame=self.modBusInterface.slaveRx(self.interfaceAddress);
				
				#if a frame has been received
				if (frame):
					self.logger.info('A frame has been received');

					#reset timeout
					self.lastSynchroTimestamp=time.time();

					#todo reflesh below function specific to Diematic3 to get registers content
					#self.refreshRegisters()
					
					#refresh regulator attribute
					#self.refreshAttributes();

					#check time drift
					# check self.datetime exist before running these lines
					#now = datetime.datetime.now().astimezone();
					#self.logger.debug('Now :' + str(now));
					#self.logger.debug('Boiler :' + str(self.datetime));
					#drift = (now - self.datetime).total_seconds();
					drift=0;
					self.logger.debug('Drift :' + str(drift));
					
					#if drift is more than 60 s
					if (self.syncTime and abs(drift) >=60):
						self.overDriftCounter+=1;
						self.logger.debug('Drift Counter:' + str(self.overDriftCounter));
						# more than 6 successive times
						if (self.overDriftCounter >=6):
							#boiler time is set
							self.overDriftCounter=0;
							self.logger.critical('Sync Time: Set boiler time to :' + str(now));
							self.datetime=now;
					else:
						self.overDriftCounter=0;
									
								
				if ((time.time()-self.lastSynchroTimestamp) > VALIDITY_TIME):
					#log
					self.logger.warning('Synchro timeout');
					#init regulator register
					self.initAttributes();
					#publish values
					self.updateCallback();
					#reinit connection
					self.initConnection();
					#reset timeout
					self.lastSynchroTimestamp=time.time();
					

			self.logger.critical('Modbus Thread stopped');
		except BaseException as exc:		
			self.logger.exception(exc)
