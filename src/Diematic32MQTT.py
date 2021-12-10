#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys,signal,threading
import configparser
import logging, logging.config
import DDModbus,Diematic3Panel
import paho.mqtt.client as mqtt
import json
import time,datetime

class MessageBuffer:
	def __init__(self,mqtt):
		#logger
		self.logger = logging.getLogger(__name__);
		
		self.buffer=dict();
		self.mqtt=mqtt;
	
	def update(self,topic,value):
		#if the topic is not in buffer
		if ((topic not in self.buffer) or (self.buffer[topic]['value']!=value)):
			self.buffer[topic]={'value':value,'update':True};
		
	def send(self):
		#for each topic
		for topic in self.buffer:
			if self.buffer[topic]['update']:
				#send message without trailing / on topic
				if (topic!=''):
					self.mqtt.publish(mqttTopicRoot+'/'+topic,self.buffer[topic]['value'],1,True);
					self.logger.info('Publish :'+mqttTopicRoot+'/'+topic+' '+self.buffer[topic]['value'])
				else:
					self.mqtt.publish(mqttTopicRoot,self.buffer[topic]['value'],1,True);
					self.logger.info('Publish :'+mqttTopicRoot+' '+self.buffer[topic]['value'])
				#set the flag to False
				self.buffer[topic]['update']=False;
	
	
def diematic3Publish(self):
	def floatValue(parameter):
		return (f"{parameter:.1f}" if parameter is not None else '');
	def intValue(parameter):
		return (f"{parameter:d}" if parameter is not None else '');
		
	#boiler
	buffer.update('date',self.datetime.isoformat() if self.datetime is not None else '');
	buffer.update('type',intValue(self.type));
	buffer.update('release',intValue(self.release));
	buffer.update('ext/temp',floatValue(self.extTemp));
	buffer.update('temp',floatValue(self.temp));
	buffer.update('targetTemp',floatValue(self.targetTemp));
	buffer.update('returnTemp',floatValue(self.returnTemp));
	buffer.update('waterPressure',floatValue(self.waterPressure));
	buffer.update('power',intValue(self.burnerPower));
	buffer.update('smokeTemp',floatValue(self.smokeTemp));
	buffer.update('fanSpeed',intValue(self.fanSpeed));
	buffer.update('burnerStatus',intValue(self.burnerStatus));
	buffer.update('pumpPower',intValue(self.pumpPower));
	buffer.update('alarm',json.dumps(self.alarm));
	
	#hotwater
	buffer.update('hotWater/pump',intValue(self.hotWaterPump));
	buffer.update('hotWater/temp',floatValue(self.hotWaterTemp));
	buffer.update('hotWater/mode',self.hotWaterMode if self.hotWaterMode is not None else '');
	buffer.update('hotWater/dayTemp',floatValue(self.hotWaterDayTargetTemp));
	buffer.update('hotWater/nightTemp',floatValue(self.hotWaterNightTargetTemp));
	
	#area A
	buffer.update('zoneA/temp',floatValue(self.zoneATemp));
	buffer.update('zoneA/mode',self.zoneAMode if self.zoneAMode is not None else '');
	buffer.update('zoneA/pump',intValue(self.zoneAPump));
	buffer.update('zoneA/dayTemp',floatValue(self.zoneADayTargetTemp));
	buffer.update('zoneA/nightTemp',floatValue(self.zoneANightTargetTemp));
	buffer.update('zoneA/antiiceTemp',floatValue(self.zoneAAntiiceTargetTemp));

	#area B
	buffer.update('zoneB/temp',floatValue(self.zoneBTemp));
	buffer.update('zoneB/mode',self.zoneBMode if self.zoneBMode is not None else '');
	buffer.update('zoneB/pump',intValue(self.zoneBPump));
	buffer.update('zoneB/dayTemp',floatValue(self.zoneBDayTargetTemp));
	buffer.update('zoneB/nightTemp',floatValue(self.zoneBNightTargetTemp));
	buffer.update('zoneB/antiiceTemp',floatValue(self.zoneBAntiiceTargetTemp));
	
	#send MQTT messages
	buffer.send();
	
def on_connect(client, userdata, flags, rc):		
	logger.critical('Connected to MQTT broker');
	print('Connected to MQTT broker');
	#subscribe to control messages with Q0s of 2
	client.subscribe(mqttTopicRoot+'/+/+/set',2);
	client.subscribe(mqttTopicRoot+'/date/set',2);
	
	#online publish
	client.publish(mqttTopicRoot,'Online',1,True);
	logger.info('Publish :'+mqttTopicRoot+' '+'Online');
	
def on_disconnect(client, userdata, rc):
	logger.critical('Diconnected from MQTT broker');
	
def modeSet(client, userdata, message):
	#table for topic to attribute bind
	table={'/hotWater/mode/set':'hotWaterMode',
		'/zoneA/mode/set':'zoneAMode',
		'/zoneB/mode/set':'zoneBMode'};
		
	#remove root of the topic
	shortTopic=message.topic[len(mqttTopicRoot):]
	
	#if topic exist
	if shortTopic in table:
		#process it
		setattr(panel,table[shortTopic],message.payload.decode());
		logger.info(shortTopic+' : '+str(message.payload));
	else:
		logger.warning('Unknown topic : '+shortTopic);

def tempSet(client, userdata, message):	
	#table for topic to attribute bind
	table={'/hotWater/dayTemp/set':'hotWaterDayTargetTemp',
		'/hotWater/nightTemp/set':'hotWaterNightTargetTemp',
		'/zoneA/dayTemp/set':'zoneADayTargetTemp',
		'/zoneA/nightTemp/set':'zoneANightTargetTemp',
		'/zoneA/antiiceTemp/set':'zoneAAntiiceTargetTemp',
		'/zoneB/dayTemp/set':'zoneBDayTargetTemp',
		'/zoneB/nightTemp/set':'zoneBNightTargetTemp',
		'/zoneB/antiiceTemp/set':'zoneBAntiiceTargetTemp'};
		
	#remove root of the topic
	shortTopic=message.topic[len(mqttTopicRoot):]
	
	try:
		value=float(message.payload);
	except (ValueError,OverflowError):
		logger.warning('Value error :'+str(message.payload));
		return
	
	#if topic exist
	if shortTopic in table:
		#process it
		setattr(panel,table[shortTopic],value);
		logger.info(shortTopic+' : '+str(value));
	else:
		logger.warning('Unknown topic : '+shortTopic);

def dateSet(client, userdata, message):
	#table for topic to attribute bind
	table={'/date/set':'datetime'};
		
	#remove root of the topic
	shortTopic=message.topic[len(mqttTopicRoot):]
	
	#if topic exist
	if shortTopic in table:
		#process it
		logger.info(shortTopic+' : '+str(message.payload));
		if (message.payload.decode()=='Now'):
			setattr(panel,table[shortTopic],datetime.datetime.now().astimezone());
	else:
		logger.warning('Unknown topic : '+shortTopic);

def paramSet(client, userdata, message):
	try:
		logger.debug('MQTT msg received :'+message.topic+' '+str(message.payload));
		if (message.topic[-8:]=='Temp/set'):
			tempSet(client, userdata, message);
		elif (message.topic[-8:]=='mode/set'):
			modeSet(client, userdata, message);
		elif (message.topic[-8:]=='date/set'):
			dateSet(client, userdata, message);
	except BaseException as exc:	
		logger.exception(exc);

def sigterm_exit(signum, frame):
		logger.critical('Stop requested by SIGTERM, raising KeyboardInterrupt');
		raise KeyboardInterrupt;


if __name__ == '__main__':

	# Initialisation Logger
	logging.config.fileConfig('logging.conf');
	logger = logging.getLogger(__name__);
	
	#Sigterm trapping
	signal.signal(signal.SIGTERM, sigterm_exit);
	try:
		#Initialisation config
		config = configparser.ConfigParser()
		config.read('Diematic32MQTT.conf')

		#Modbus settings
		modbusAddress=config.get('Modbus','ip');
		modbusPort=config.get('Modbus','port');
		modbusRegulatorAddress=int(config.get('Modbus','regulatorAddress'),0);
		logger.critical('Modbus interface address: '+modbusAddress+' : '+modbusPort);
		logger.critical('Modbus regulator address: '+ hex(modbusRegulatorAddress));
		
		#boiler time timezone
		boilerTimezone=config.get('Boiler','timezone');
		
		#MQTT settings
		mqttBrokerHost=config.get('MQTT','brokerHost');
		mqttBrokerPort=config.get('MQTT','brokerPort');
		mqttTopicRoot=config.get('MQTT','topicRoot');
		logger.critical('Broker: '+mqttBrokerHost+' : '+mqttBrokerPort);
		logger.critical('Topic Root: '+mqttTopicRoot);		
		
		#init panel
		Diematic3Panel.Diematic3Panel.updateCallback=diematic3Publish;
		panel=Diematic3Panel.Diematic3Panel(modbusAddress,int(modbusPort),modbusRegulatorAddress,boilerTimezone);
		

		#init mqtt brooker
		client = mqtt.Client()
		client.on_connect = on_connect
		client.on_disconnect = on_disconnect
		#last will
		client.will_set(mqttTopicRoot,"Offline",1,True)
		client.connect_async(mqttBrokerHost, int(mqttBrokerPort))
		client.message_callback_add(mqttTopicRoot+'/+/+/set',paramSet)
		client.message_callback_add(mqttTopicRoot+'/date/set',paramSet)		
		client.loop_start()
		#create mqtt message buffer
		buffer=MessageBuffer(client);
			

		#start modbus thread
		panel.loop_start();
		run=True;
		while run:
			#check every 10s that all threads are living
			time.sleep(5);
			if (threading.active_count()!=3):
				logger.critical('At least one process has been killed, stop launched');
				run=False;
		#stop modbus thread
		panel.loop_stop();		
		#disconnect mqtt server
		client.loop_stop();
		logger.critical('Stopped');
	except KeyboardInterrupt:
		#stop modbus thread
		panel.loop_stop();

		#disconnect mqtt server
		client.loop_stop();
		logger.critical('Stopped by KeyboardInterrupt');
	except BaseException as exc:	
		logger.exception(exc);


			



	
		

  










