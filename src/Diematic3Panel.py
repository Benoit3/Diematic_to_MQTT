#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading,queue
import logging, logging.config
import DDModbus
import time,datetime,pytz
from enum import IntEnum
from Diematic import Diematic,DDREGISTER

#definition for state machine used for modBus data exchange
class DDModBusStatus(IntEnum):
	INIT=0;
	SLAVE=1;
	MASTER=2;

#This class allow to read/write parameters to Diematic3 regulator with the helo of a RS485/TCPIP converter
#refresh of attributes From regulator is done roughly every minute
#update request to the regulator are done within 10 s and trigger a whole read refresh
class Diematic3Panel(Diematic):
	def __init__(self,ip,port,regulatorAddress,interfaceAddress,boilerTimezone='',syncTime=False):
		
		#state machine initialisation
		self.busStatus=DDModBusStatus.INIT;
		
		super().__init__(ip,port,regulatorAddress,0,boilerTimezone,syncTime)

#this property is used to get register values from the regulator Diematic3
	def refreshRegisters(self):
		#update registers 1->63
		reg=self.modBusInterface.masterReadAnalog(self.regulatorAddress,1,63);
		if (reg is not None):
			self.registers.update(reg);
		else:
			return(False);
		#update registers 64->127
		reg=self.modBusInterface.masterReadAnalog(self.regulatorAddress,64,64);
		if (reg is not None):
			self.registers.update(reg);
		else:
			return(False);
			
		#update registers 128->191
		#reg=self.modBusInterface.masterReadAnalog(self.regulatorAddress,128,64);
		#if (reg is not None):
		#	self.registers.update(reg);
		#else:
		#	return(False);
			
		#update registers 191->255
		#reg=self.modBusInterface.masterReadAnalog(self.regulatorAddress,192,64);
		#if (reg is not None):
		#	self.registers.update(reg);
		#else:
		#	return(False);
			
		#update registers 384->447
		reg=self.modBusInterface.masterReadAnalog(self.regulatorAddress,384,64);
		if (reg is not None):
			self.registers.update(reg);
		else:
			return(False);
		#update registers 448->470
		reg=self.modBusInterface.masterReadAnalog(self.regulatorAddress,448,23);	
		if (reg is not None):
			self.registers.update(reg);
		else:
			return(False);
		
		#display register table on standard output
		#regLine="";
		#for index in range(256):
		#	try:
		#		regLine+='{:04X}'.format(self.registers[index])+' '
		#	except KeyError:
		#		regLine+='---- ';
				
		#	if (index % 16)==15:
		#		regLine= '{:01X}'.format(index >>4)+'0: '+regLine
		#		print(regLine);
		#		regLine='';

		#print('==========================================')
		return(True);


#this property is used by the Modbus loop to set register dedicated to Mode A and hotwater mode (in case of no usage of B area)		
	def modeAUpdate(self):
		#if mode A register update request is pending
		if (not(self.zoneAModeUpdateRequest.empty()) or (not(self.hotWaterModeUpdateRequest.empty()) and (self.zoneBMode is None))):
			#get current mode
			currentMode=self.modBusInterface.masterReadAnalog(self.regulatorAddress,DDREGISTER.MODE_A.value,1);
			#in case of success
			if (currentMode):
				mode=currentMode[DDREGISTER.MODE_A];
				self.logger.info('Mode A current value :'+str(mode));
				
				#update mode with mode requests					
				if (not(self.zoneAModeUpdateRequest.empty())):
					mode= (mode & 0x50) | self.zoneAModeUpdateRequest.get();
					
				if (not(self.hotWaterModeUpdateRequest.empty()) and (self.zoneBMode is None)):
					mode= (mode & 0x2F) | self.hotWaterModeUpdateRequest.get();

				self.logger.info('Mode A next value :'+str(mode));
				#specific case for antiice request
				#following write procedure is an empirical solution to have remote control refresh while updating mode
				if (mode==1):
					#set antiice day number to 1
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[1]);
					time.sleep(0.5);
					#set antiice day number to 0
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[0]);
					#set mode A number to requested value
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_A.value,[mode]);

				#general case
				#following write procedure is an empirical solution to have remote control refresh while updating mode
				else:
					#set mode A
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_A.value,[mode]);
					#set antiice day number to 1
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[1]);
					#set mode A again
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_A.value,[mode]);
					time.sleep(0.5);
					#set mode A again
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_A.value,[mode]);
					#set antiice day number to 0
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[0]);
			
				#request register refresh
				self.refreshRequest=True;

#this property is used by the Modbus loop to set register dedicated to Mode B and hotwater mode (in case of usage of B area)					
	def modeBUpdate(self):
		#if mode B register update request is pending
		if (not(self.zoneBModeUpdateRequest.empty()) or (not(self.hotWaterModeUpdateRequest.empty()) and (self.zoneBMode))):
			#get current mode
			currentMode=self.modBusInterface.masterReadAnalog(self.regulatorAddress,DDREGISTER.MODE_B.value,1);
			#in case of success
			if (currentMode):
				mode=currentMode[DDREGISTER.MODE_B];
				self.logger.info('Mode B current value :'+str(mode));
				
				#update mode with mode requests					
				if (not(self.zoneBModeUpdateRequest.empty())):
					mode= (mode & 0x50) | self.zoneBModeUpdateRequest.get();
					
				if (not(self.hotWaterModeUpdateRequest.empty()) and (self.zoneBMode)):
					mode= (mode & 0x2F) | self.hotWaterModeUpdateRequest.get();

				self.logger.info('Mode B next value :'+str(mode));
				#specific case for antiice request
				#following write procedure is an empirical solution to have remote control refresh while updating mode
				if (mode==1):
					#set antiice day number to 1
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[1]);
					time.sleep(0.5);
					#set antiice day number to 0
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[0]);
					#set mode B number to requested value
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_B.value,[mode]);

				#general case
				#following write procedure is an empirical solution to have remote control refresh while updating mode
				else:
					#set mode B
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_B.value,[mode]);
					#set antiice day number to 1
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[1]);
					#set mode B again
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_B.value,[mode]);
					time.sleep(0.5);
					#set mode B again
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.MODE_B.value,[mode]);
					#set antiice day number to 0
					self.modBusInterface.masterWriteAnalog(self.regulatorAddress,DDREGISTER.NB_JOUR_ANTIGEL.value,[0]);
			
				#request refresh
				self.refreshRequest=True;					

#modbus loop, shall run in a specific thread. Allow to exchange register values with the Dielatic regulator
	def loop(self):
		#parameter validity duration in seconds after expiration of period
		#after this timeout, interface is reset
		VALIDITY_TIME=30
		try:
			self.masterSlaveSynchro=False 
			self.run=True;
			#reset timeout
			self.lastSynchroTimestamp=time.time();
			while self.run:
				#wait for a frame received
				frame=self.modBusInterface.slaveRx(self.interfaceAddress);

				#depending current bus mode	
				if (self.busStatus!=DDModBusStatus.SLAVE):
					if (frame):
						#switch mode to slave
						self.busStatus=DDModBusStatus.SLAVE;
						self.slaveTime=time.time();
						self.logger.debug('Bus status switched to SLAVE');
						
				elif (self.busStatus==DDModBusStatus.SLAVE):
					slaveModeDuration=time.time()-self.slaveTime;
					#if no frame have been received and slave happen during at least 5s
					if ((not frame) and (slaveModeDuration>5)):
						#switch mode to MASTER
						self.masterTime=time.time();
						self.busStatus=DDModBusStatus.MASTER;
						self.logger.debug('Bus status switched to MASTER after '+str(slaveModeDuration));
						
						#if the state wasn't still synchronised
						if (not self.masterSlaveSynchro):
							self.logger.info('ModBus Master Slave Synchro OK');
							self.masterSlaveSynchro=True;
							
						#mode A register update if needed
						self.modeAUpdate();
						
						#mode B register update if needed
						self.modeBUpdate();
								
						#while general register update request are pending and Master mode is started since less than 2s
						while (not(self.regUpdateRequest.empty()) and ((time.time()-self.masterTime) < 2)):
							regSet=self.regUpdateRequest.get(False)
							self.logger.debug('Write Request :'+str(regSet.address)+':'+str(regSet.data));
							#write to Analog registers
							if ( not self.modBusInterface.masterWriteAnalog(self.regulatorAddress,regSet.address,regSet.data)):
								#And cancel Master Slave Synchro Flag in case of error

								self.logger.warning('ModBus Master Slave Synchro Error');
								self.masterSlaveSynchro=False;
							self.refreshRequest=True;
							
						
						#update registers, todo condition for refresh launch
						if (((time.time()-self.lastSynchroTimestamp) > (self.refreshPeriod-5)) or self.refreshRequest):
							if (self.refreshRegisters()):
								self.lastSynchroTimestamp=time.time();
							
								#refresh regulator attribute
								self.refreshAttributes();
								
								#clear Flag
								self.refreshRequest=False;
								
								#check time drift
								now = datetime.datetime.now().astimezone();
								self.logger.debug('Now :' + str(now));
								self.logger.debug('Boiler :' + str(self.datetime));
								drift = (now - self.datetime).total_seconds();
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
									
							else:
								#Cancel Master Slave Synchro Flag in case of error
								self.logger.warning('ModBus Master Slave Synchro Error');
								self.masterSlaveSynchro=False;
								
				if ((time.time()-self.lastSynchroTimestamp) > self.refreshPeriod + VALIDITY_TIME):
					#log
					self.logger.warning('Synchro timeout');
					#init regulator register
					self.initAttributes();
					#publish values
					self.updateCallback();
					#reinit connection
					self.initConnection();
					self.refreshRequest=True;
					#reset timeout
					self.lastSynchroTimestamp=time.time();
					

			self.logger.critical('Modbus Thread stopped');
		except BaseException as exc:		
			self.logger.exception(exc)
