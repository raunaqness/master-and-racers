import time
import redis
import sys
import json
import os
from subprocess import check_output

class Racer:

	def __init__(self):

		# Redis variables
		self.redis_client = redis.Redis(host='redis', port=6379, db=0)
		self.subscriber = self.redis_client.pubsub()

		self.racer_num = self.get_racer_num()
		self.time_delay = float(os.getenv("time_delay", 0.050))

		# Racer name log on init
		print("R{}".format(self.racer_num))

		self.master_to_racer_channel_name = "MASTER_TO_RACER_{}".format(self.racer_num)
		self.subscriber.subscribe(self.master_to_racer_channel_name)

		self.racer_to_master_channel_name = "RACER_TO_MASTER_{}".format(self.racer_num)
		self.publish_channel_name = self.racer_to_master_channel_name
		self.waiting_for_master_input = True

		# class variables
		self.continue_racing = False

		self.m = 0
		self.c = 0
		self.x = 0
		self.y = 0

	def start(self):

		# event loop starts
		while True:

			message = self.subscriber.get_message()

			if message:

				# usually the first message, need to skip this
				if message['type'] == 'subscribe':
					continue

				# received data from master process
				data = json.loads(message['data'])

				if data['message_type'] == "KILL":
					sys.exit(0)

				# message received from master contains new [mi, ci]
				print("Received message from M. 'm' : {} 'c' : {}".format(data['m'], data['c']))

				self.m = data['m']
				self.c = data['c']
				self.x = 0

				self.continue_racing = True

			# Calculate Next value
			if self.continue_racing:
				self.x += 1
				self.y = self.m * self.x + self.c

				data = {
						'timestamp' : time.time(),
						'racer_num' : self.racer_num, 
						'x' : self.x, 
						'y' : self.y
					   }

				self.redis_client.publish(self.publish_channel_name, json.dumps(data))

				time.sleep(self.time_delay)


	def get_racer_num(self):

		# Get current docker container id
		command = "head -1 /proc/self/cgroup|cut -d/ -f3"
		output = check_output(command, shell=True)
		container_id = output.decode()[:-1]

		# get docker image name from container id
		command = '''docker inspect --format="{{.Name}}" ''' + container_id
		output = check_output(command, shell=True)
		image_name = output.decode()[:-1]

		racer_num = image_name.split('racer_')[-1]

		return int(racer_num)

R = Racer()
R.start()
