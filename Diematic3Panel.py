#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading,traceback
import logging, logging.config
import DDModbus
import time,datetime,pytz
from enum import IntEnum

#parameter validity duration in seconds
VALIDITY_TIME=120

#parameter refresh period
REFRESH_PERIOD=52


class DDModBusStatus(IntEnum):
	INIT=0;
	SLAVE=1;
	MASTER=2;

class DDREGISTER(IntEnum):
	CTRL=3;
	HEURE=4;
	MINUTE=5;
	JOUR_SEMAINE=6;
	TEMP_EXT=7;
	NB_JOUR_ANTIGEL=13;
	CONS_JOUR_A=14;
	CONS_NUIT_A=15;
	CONS_ANTIGEL_A=16;
	MODE_A=17;
	TEMP_AMB_A=18;
	TCALC_A=21;
	CONS_JOUR_B=23;
	CONS_NUIT_B=24;
	CONS_ANTIGEL_B=25;
	MODE_B=26;
	TEMP_AMB_B=27;
	TCALC_B=32;
	CONS_ECS=59;
	TEMP_ECS=62;
	TEMP_CHAUD=75;
	CONS_ECS_NUIT=96;
	JOUR=108;
	MOIS=109;
	ANNEE=110;
	BASE_ECS=427;
	OPTIONS_B_C=428;
	RETURN_TEMP=453;
	SMOKE_TEMP=454;
	FAN_SPEED=455;
	PRESSION_EAU=456;
	BOILER_TYPE=457;
	PUMP_POWER=463;
	ALARME=465;
	
	
class Diematic3Panel:
	updateCallback=None;
	def __init__(self,ip,port,regulatorAddress,boilerTimezone):
		
		#logger
		self.logger = logging.getLogger(__name__);
		
		#interface init
		self.modBusInterface=DDModbus.DDModbus(ip,port);
		self.modBusInterface.clean();
		
		#regulator modbus address
		self.regulatorAddress=regulatorAddress;
		
		#timezone
		self.boilerTimezone=boilerTimezone;
		
		#status init to master state
		self.busStatus=DDModBusStatus.INIT;
		
		#register creation
		self.registers=dict();
		
		#regulator attributes
		self.initRegulator();
		
	def initRegulator(self):
		#regulator attributes
		self.datetime=None;
		self.type=None;
		self.release=None;
		self.extTemp=None;
		self.temp=None;
		self.targetTemp=None;
		self.returnTemp=None;
		self.waterPressure=None;
		self.burnerPower=None;
		self.smokeTemp=None;
		self.fanSpeed=None;
		self.burnerStatus=None;
		self.pumpPower=None;
		self.alarm={'id':None,'txt':None};
		self.hotWaterPump=None;
		self.hotWaterTemp=None;
		self.hotWaterMode=None;
		self.hotWaterDayTargetTemp=None;
		self.hotWaterNightTargetTemp=None;
		self.zoneATemp=None;
		self.zoneAMode=None;
		self.zoneAPump=None;
		self.zoneADayTargetTemp=None;
		self.zoneANightTargetTemp=None;
		self.zoneAAntiiceTargetTemp=None;
		self.zoneBTemp=None;
		self.zoneBMode=None;
		self.zoneBPump=None;
		self.zoneBDayTargetTemp=None;
		self.zoneBNightTargetTemp=None;
		self.zoneBAntiiceTargetTemp=None;
	
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
			return(True);
		else:
			return(False);
	
	def float10(self,reg):
		if (reg==0xFFFF):
			return None;
		if (reg >= 0x8000):
			reg=-(reg & 0x7FFF)
		return(reg*0.1);
	
	def refreshAttributes(self):
		FAN_SPEED_MIN=1000;
		FAN_SPEED_MAX=6000;
		
		#boiler
		self.datetime=datetime.datetime(self.registers[DDREGISTER.ANNEE]+2000,self.registers[DDREGISTER.MOIS],self.registers[DDREGISTER.JOUR],self.registers[DDREGISTER.HEURE],self.registers[DDREGISTER.MINUTE],0,0,pytz.timezone(self.boilerTimezone));
		self.type=self.registers[DDREGISTER.BOILER_TYPE];
		self.release=self.registers[DDREGISTER.CTRL];
		self.extTemp=self.float10(self.registers[DDREGISTER.TEMP_EXT]);
		self.temp=self.float10(self.registers[DDREGISTER.TEMP_CHAUD]);
		self.targetTemp=self.float10(self.registers[DDREGISTER.TCALC_A]);
		self.returnTemp=self.float10(self.registers[DDREGISTER.RETURN_TEMP]);
		self.waterPressure=self.float10(self.registers[DDREGISTER.PRESSION_EAU]);
		if ( self.registers[DDREGISTER.FAN_SPEED]>= FAN_SPEED_MIN):
			self.burnerPower=10*round((self.registers[DDREGISTER.FAN_SPEED] / FAN_SPEED_MAX)*10);
		else:
			self.burnerPower=0;
		self.smokeTemp=self.float10(self.registers[DDREGISTER.SMOKE_TEMP]);
		self.fanSpeed=self.registers[DDREGISTER.FAN_SPEED];
		self.burnerStatus=(self.registers[DDREGISTER.BASE_ECS] & 0x08) >>3;
		self.pumpPower=self.registers[DDREGISTER.PUMP_POWER];
		self.alarm['id']=self.registers[DDREGISTER.ALARME];
		alarmId=self.alarm['id'];
		if (alarmId==0):
			self.alarm['txt']='OK';
		elif (alarmId==10):
			self.alarm['txt']='Défaut Sonde Retour';
		elif (alarmId==21):
			self.alarm['txt']='Pression d\'eau basse';
		elif (alarmId==26):
			self.alarm['txt']='Défaut Allumage';
		elif (alarmId==27):
			self.alarm['txt']='Flamme Parasite';
		elif (alarmId==28):
			self.alarm['txt']='STB Chaudière';
		elif (alarmId==30):
			self.alarm['txt']='Rearm. Coffret';	
		elif (alarmId==31):
			self.alarm['txt']='Défaut Sonde Fumée';
		else:
			self.alarm['txt']='Défaut inconnu';
		
		#hotwater
		self.hotWaterPump=(self.registers[DDREGISTER.BASE_ECS] & 0x20) >>5;
		self.hotWaterTemp=self.float10(self.registers[DDREGISTER.TEMP_ECS]);
		if ((self.registers[DDREGISTER.MODE_A] & 0x50) ==0):
			self.hotWaterMode='AUTO';
		elif ((self.registers[DDREGISTER.MODE_A] & 0x50) ==0x50):
			self.hotWaterMode='TEMP';
		elif ((self.registers[DDREGISTER.MODE_A] & 0x50) ==0x10):
			self.hotWaterMode='PERM';
		else:
			self.hotWaterMode=None;
		self.hotWaterDayTargetTemp=self.float10(self.registers[DDREGISTER.CONS_ECS]);
		self.hotWaterNightTargetTemp=self.float10(self.registers[DDREGISTER.CONS_ECS_NUIT]);
		
		#Area A
		self.zoneATemp=self.float10(self.registers[DDREGISTER.TEMP_AMB_A]);
		if ( self.zoneATemp is not None):
			modeA=self.registers[DDREGISTER.MODE_A]& 0x2F;
			if (modeA==8):
				self.zoneAMode='AUTO';
			elif (modeA==36):
				self.zoneAMode='TEMP JOUR';
			elif (modeA==34):
				self.zoneAMode='TEMP NUIT';
			elif (modeA==4):
				self.zoneAMode='PERM JOUR';
			elif (modeA==2):
				self.zoneAMode='PERM NUIT';
			elif (modeA==1):
				self.zoneAMode='ANTIGEL';
				
			self.zoneAPump=(self.registers[DDREGISTER.BASE_ECS] & 0x10) >>4;
			self.zoneADayTargetTemp=self.float10(self.registers[DDREGISTER.CONS_JOUR_A]);
			self.zoneANightTargetTemp=self.float10(self.registers[DDREGISTER.CONS_NUIT_A]);
			self.zoneAAntiiceTargetTemp=self.float10(self.registers[DDREGISTER.CONS_ANTIGEL_A]);

		else:
			self.zoneAMode=None;
			self.zoneAPump=None;
			self.zoneADayTargetTemp=None;
			self.zoneANightTargetTemp=None;
			self.zoneAAntiiceTargetTemp=None;

				
		#Area B
		self.zoneBTemp=self.float10(self.registers[DDREGISTER.TEMP_AMB_B]);
		if ( self.zoneBTemp is not None):
			modeB=self.registers[DDREGISTER.MODE_B]& 0x2F;
			if (modeB==8):
				self.zoneBMode='AUTO';
			elif (modeB==36):
				self.zoneAMode='TEMP JOUR';
			elif (modeB==34):
				self.zoneBMode='TEMP NUIT';
			elif (modeB==4):
				self.zoneBMode='PERM JOUR';
			elif (modeB==2):
				self.zoneBMode='PERM NUIT';
			elif (modeB==1):
				self.zoneBMode='ANTIGEL';
				
			self.zoneBPump=(self.registers[DDREGISTER.OPTIONS_B_C] & 0x10) >>4;
			self.zoneBDayTargetTemp=self.float10(self.registers[DDREGISTER.CONS_JOUR_B]);
			self.zoneBNightTempTarget=self.float10(self.registers[DDREGISTER.CONS_NUIT_B]);
			self.zoneBAntiiceTempTarget=self.float10(self.registers[DDREGISTER.CONS_ANTIGEL_B]);

		else:
			self.zoneBMode=None;
			self.zoneBPump=None;
			self.zoneBDayTargetTemp=None;
			self.zoneBNightTempTarget=None;
			self.zoneBAntiiceTempTarget=None;

		self.updateCallback();
	
	def loop(self):
		self.run=True;
		self.lastSynchroTimestamp=0;
		while self.run:
			#wait for a frame received
			frame=self.modBusInterface.slaveRx();

			#depending current bus mode	
			if (self.busStatus!=DDModBusStatus.SLAVE):
				if (frame):
					#switch mode to slave
					self.busStatus=DDModBusStatus.SLAVE;
					self.logger.debug('Bus status switched to SLAVE');
					
			elif (self.busStatus==DDModBusStatus.SLAVE):
				if (not frame):
					#switch mode to MASTER
					self.busStatus=DDModBusStatus.MASTER;
					self.logger.debug('Bus status switched to MASTER');
					
					#update registers, todo condition for refresh launch
					if ((time.time()-self.lastSynchroTimestamp) > REFRESH_PERIOD):
						if (self.refreshRegisters()):
							self.lastSynchroTimestamp=time.time();
						
							#refresh regulator attribute
							self.refreshAttributes();
							
			if ((time.time()-self.lastSynchroTimestamp) > VALIDITY_TIME):
				self.logger.debug('Init Regulator');
				self.initRegulator();
				self.updateCallback();
				
	def loop_start(self):
		self.loopThread = threading.Thread(target=self.loop)
		self.loopThread.start();
		
	def loop_stop(self):
		self.run=False;
		self.loopThread.join();
