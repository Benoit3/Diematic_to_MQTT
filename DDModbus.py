#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import logging
import socket
import traceback

def calc_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos 
        for i in range(8):
            if ((crc & 1) != 0):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

#class used to define a structure of several continuous registers
class RegisterSet:
	address=0;
	data=list();
	
	def __str__(self):
		return('Reg:'+str(self.address)+' data: '+str(self.data));
  
class slaveRequest:
	FRAME_MIN_LENGTH=0x08;
	FRAME_MAX_LENGTH=0x100;
	
	def __init__(self,data):
		#logger
		self.logger = logging.getLogger(__name__)
		self.valid=False;
		self.modbusAddress=0;
		self.R_W=False;
		self.regAddress=0;
		self.regNb=0;
		self.data=dict();
		
		#check rough length
		if ((len(data) > self.FRAME_MAX_LENGTH) or (len(data) < self.FRAME_MIN_LENGTH )):
			self.logger.warning('Received Frame Length Error');
			return;
	
		#if modBus feature is READ_ANALOG_HOLDING_REGISTERS
		if (data[1] == DDModbus.READ_ANALOG_HOLDING_REGISTERS):				
			#check CRC
			crc=calc_crc(data[0:6]);
			if (crc!=0x100*data[7]+data[6]):
				self.logger.warning('READ_ANALOG_HOLDING_REGISTERS frame CRC error ');
				return;
			
			#save request informations
			self.valid=True;
			self.modbusAddress=data[0];
			self.R_W=True;
			self.regAddress=0x100*data[2]+data[3];
			self.regNb=0x100*data[4]+data[5];

			
		#if modBus feature is WRITE_MULTIPLE_REGISTERS			
		if (data[1] == DDModbus.WRITE_MULTIPLE_REGISTERS):
			#get register number
			regNumber=data[4]*0x100 + data[5];

			#check that byte nb is twice register number
			if (2*regNumber != data[6]):
				self.logger.warning('WRITE_MULTIPLE_REGISTERS reg nb inconsistency');
				return;
				
			#calculate waited frame length
			frameLength=2*regNumber+9;

			#check frame size is not too short according waited frameLength
			if (frameLength > len(data)):
				self.logger.warning('WRITE_MULTIPLE_REGISTERS frame too short');
				return;
			
			#check CRC
			crc=calc_crc(data[0:frameLength-2]);
			if (crc!=0x100*data[frameLength-1]+data[frameLength-2]):
				self.logger.warning('WRITE_MULTIPLE_REGISTERS frame CRC error '+hex(crc));
				return;
				
			#save request informations
			self.valid=True;
			self.modbusAddress=data[0];
			self.R_W=False;
			self.regAddress=0x100*data[2]+data[3];
			self.regNb=0x100*data[4]+data[5];
			for i in range(0,self.regNb):
				self.data[self.regAddress+i]=0x100*data[7+2*i]+data[8+2*i];
			
	
class DDModbus:
	ip=None; #serial port id
	port=None;
	CLEANING_TIMEOUT=0.1;
	FRAME_RX_TIMEOUT=2.0;
	READ_ANALOG_HOLDING_REGISTERS=0x03;
	WRITE_MULTIPLE_REGISTERS=0x10;
	
	ANSWER_FRAME_MIN_LENGTH=0x07;
	ANSWER_FRAME_MAX_LENGTH=0x100;

	def __init__(self,ip,port):
		#logger
		self.logger = logging.getLogger(__name__)
		
		#socket definition and connection
		self.ip=ip;
		self.port=port;
		self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM);
		self.socket.connect((self.ip,self.port));
		
	def clean(self):
		run= True;
		while run:
			try:
				self.socket.settimeout(DDModbus.CLEANING_TIMEOUT);
				data=self.socket.recv(1024);
				self.logger.debug('Cleaning of: '+str(len(data))+' bytes(s)');
			except socket.error as exc:
				run=False;

	def slaveRx(self):
			try:
				self.socket.settimeout(DDModbus.FRAME_RX_TIMEOUT);
				data=self.socket.recv(1024);
				self.logger.debug('Frame received: '+data.hex());
				
				#frame are never used and never acknowledged
				frame=slaveRequest(data);
				
				#exemple of ack for WRITE_MULTIPLE_REGISTERS request
				#commented to avoid to the boiler to think there are
				#boiler in //
				#if (data[1]==0x10):
				#	tx=bytearray();
				#	tx.extend(data[0:6]);
				#	crc=calc_crc(tx);
				#	tx.append(crc & 0xFF);
				#	tx.append((crc >> 8) & 0xFF);
				#	tx.append(0);
				#	self.socket.send(tx);
				
				return frame;
			except socket.error as exc:
				return False;
				
	def masterReadAnalog(self,modbusAddress,regAddress,regNb):
		
		#build request
		request=bytearray();
		request.append(modbusAddress);
		request.append(DDModbus.READ_ANALOG_HOLDING_REGISTERS);
		request.append((regAddress>>8)& 0xFF);
		request.append(regAddress & 0xFF);
		request.append((regNb>>8)& 0xFF);
		request.append(regNb & 0xFF);
		crc=calc_crc(request);
		request.append(crc & 0xFF);
		request.append((crc>>8)& 0xFF);
		request.append(0);
		
		#send it
		self.logger.debug('Send read request: '+request.hex());
		self.socket.send(request);
		
		#wait for answer
		try:
			self.socket.settimeout(DDModbus.FRAME_RX_TIMEOUT);
			answer=self.socket.recv(1024);
			self.logger.debug('Answer received: '+answer.hex());
			
			#check answer
			
			#check rough length
			if ((len(answer) > self.ANSWER_FRAME_MAX_LENGTH) or (len(answer) < self.ANSWER_FRAME_MIN_LENGTH )):
				self.logger.warning('Rough Answer Length Error');
				return;
		
			#check  modBus address
			if (answer[0] != modbusAddress):
				self.logger.warning('Answer modbus address Error');
				return;
			
			#check  modBus feature
			if (answer[1] != DDModbus.READ_ANALOG_HOLDING_REGISTERS):
				self.logger.warning('Answer modbus feature Error');
				return;
				
			#check byte nb
			if (answer[2] != 2*regNb):
				self.logger.warning('Answer byte number Error');
				return;
				
			#check length
			answerLength=5+answer[2];
			if ((len(answer) < answerLength )):
				self.logger.warning('Answer Length Error');
				return;
				
			#check CRC
			crc=calc_crc(answer[0:answerLength-2]);
			if (crc!=0x100*answer[answerLength-1]+answer[answerLength-2]):
				self.logger.warning('Answer CRC error ');
				return;
			self.logger.debug('Answer valid ');
			
			#return answer as dict
			data=dict();
			for i in range(0,regNb):
				data[regAddress+i]=0x100*answer[3+2*i]+answer[4+2*i];
			return(data);
			
		except socket.error as exc:
			self.logger.warning('No answer to masterReadAnalog');
			return;
			
	def masterWriteAnalog(self,modbusAddress,regAddress,data):
		#build request
		request=bytearray();
		#byte 0
		request.append(modbusAddress);
		#byte 1
		request.append(DDModbus.WRITE_MULTIPLE_REGISTERS);
		#byte 2 & 3
		request.append((regAddress>>8)& 0xFF);
		request.append(regAddress & 0xFF);
		#byte 4 & 5 Reg Nb
		request.append(0);
		request.append(len(data));
		#byte 6 byte Nb
		request.append(2*len(data));
		#data
		for reg in data:
			request.append((reg>>8)& 0xFF);
			request.append(reg & 0xFF);
			
		crc=calc_crc(request);
		request.append(crc & 0xFF);
		request.append((crc>>8)& 0xFF);
		request.append(0);
		
		#send it
		self.logger.info('Send write request: '+request.hex());
		self.socket.send(request);
		
		#wait for ack
		try:
			self.socket.settimeout(DDModbus.FRAME_RX_TIMEOUT);
			answer=self.socket.recv(1024);
			self.logger.debug('Ack received: '+answer.hex());
			#check ack
			waited_ack=request[0:6];
			crc=calc_crc(waited_ack);
			waited_ack.append(crc & 0xFF);
			waited_ack.append((crc>>8)& 0xFF);
			if (waited_ack==answer[0:8]):
				self.logger.info('Ack OK');
				return(True);
			else:
				self.logger.warning('Ack KO. Waited Ack was : '+waited_ack.hex());
				return(False);
			
			
		except socket.error as exc:
			self.logger.warning('No ack  to master write request');
			return(False);

