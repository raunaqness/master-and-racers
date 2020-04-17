import time
import redis
import json
import sys
import os
from subprocess import check_output
from copy import deepcopy

# Waiting for all racers to be up and running
time.sleep(5)

class Master:

	def __init__(self):

		# Redis variables
		self.redis_client = redis.Redis(host='redis', port=6379, db=0)
		self.subscriber = self.redis_client.pubsub()

		self.number_of_racers = self.get_number_of_racers()

		# Subscribe to all Racers 
		for i in range(1, self.number_of_racers + 1):
			self.subscriber.subscribe("RACER_TO_MASTER_{}".format(i))

		self.lap_start_time = 0
		self.lap_end_time = 0
		self.total_laps = 0
		self.current_lap = []
		self.maximum_laps = 10

		self.racer_latencies = {}

		self.continue_current_lap = True

	def start_new_lap(self):

		# increment value of total number of laps
		self.total_laps += 1

		# reset value of current_lap
		self.current_lap = []

		self.send_new_values_to_racers()

		self.lap_start_time = time.time()

		# reset racer_latencies variable
		self.reset_racer_latencies()

		# event loop for current lap
		while self.continue_current_lap:

			message = self.subscriber.get_message()

			if message:

				# usually the first message, need to skip this
				if message['type'] == 'subscribe':
					continue

				# received data from a racer process
				racer_data = json.loads(message['data'])

				racer_num = racer_data['racer_num']
				x = racer_data['x']
				y = racer_data['y']

				timestamp = racer_data['timestamp']

				latency = time.time() - timestamp

				# set the values of the ith racer for the current lap
				racer_current_lap_data = {'racer_num' : racer_num, 'x' : x, 'y' : y, 'latency' : latency}
				
				self.racer_latencies[int(racer_num)].append(latency)

				self.current_lap.append(racer_current_lap_data)

				# if information of all racers is stored, calculate distance between all points
				if len(self.current_lap) == self.number_of_racers:
					distance = self.max_distance_between_racers()

					if distance >= 10:
						self.continue_current_lap = False

					self.current_lap = []


		# current lap has ended
		self.lap_end_time = time.time()

		# print the required data for Master 
		self.log_master_stats()
		
		# check if more laps are remaining
		self.check_master_status()	

	def log_master_stats(self):

		# Required output format : [LapNumber, Lap, LapStart, LapEnd, TimeToCompletion, AverageLatencyR1(optional), AverageLatencyR2(optional)]

		output = []
		output.append(str(self.total_laps)) # current LapNumber	
		output.append("Lap") # Lap
		output.append(str(self.lap_start_time)) # LapStart
		output.append(str(self.lap_end_time)) # LapEnd

		time_to_completion = self.lap_end_time - self.lap_start_time
		output.append(str(round(time_to_completion * 1000, 2)) + " ms" ) # TimeToCompletion

		# Append Average Racer latencies
		for i in range(1, len(self.racer_latencies)+1):
			total_latency = sum(self.racer_latencies[i])

			average_latency = 0

			if len(self.racer_latencies[i]) > 0:
				average_latency = total_latency / len(self.racer_latencies[i])
			
			output.append((str(round(average_latency * 1000, 2)) + " ms" ))

		final_output = ' '.join(output)

		# log Master output after lap completion
		print(final_output)

	def check_master_status(self):

		if self.total_laps >= self.maximum_laps:
			self.kill_all_racers()
			sys.exit(0)

		# still more laps to go
		self.continue_current_lap = True
		self.start_new_lap()

	def read_values_from_file(self):

		try:
			f = open("/data/input.txt", "r")
			data = f.read()

			lines = data.split('\n')

			output = []

			for line in lines:
				x, y = int(line.split(' ')[0]), int(line.split(' ')[1])
				output.append([x, y])

			return output

		except Exception as e:
			print("Exception occured while reading input file.")
			sys.exit(0)

		
	def send_new_values_to_racers(self):

		# Send new 'm' and 'c' values to all racers
		new_values = self.read_values_from_file()

		n = len(new_values)

		for i in range(1, self.number_of_racers + 1):

			racer_channel_name = "MASTER_TO_RACER_{}".format(i)

			m = new_values[(i-1)%n][0]
			c = new_values[(i-1)%n][1]

			data = { 'message_type' : 'new_values', 'm' : m, 'c' : c }

			self.redis_client.publish(racer_channel_name, json.dumps(data))


	def max_distance_between_racers(self):
		
		# calculate distance here
		max_distance = 0

		for i in range(self.number_of_racers):
			for j in range(self.number_of_racers):
				if i != j:
					x1, x2 = self.current_lap[i]['x'], self.current_lap[j]['x']
					y1, y2 = self.current_lap[i]['y'], self.current_lap[j]['y']

					distance = (((x2 - x1) ** 2) + ((y2 - y1) ** 2)) ** 2

					max_distance = max(max_distance, distance)

		return max_distance

	def kill_all_racers(self):
		for i in range(1, self.number_of_racers + 1):

			racer_channel_name = "MASTER_TO_RACER_{}".format(i)

			data = { 'message_type' : 'KILL' }

			self.redis_client.publish(racer_channel_name, json.dumps(data))

	def get_number_of_racers(self):

		cmd = ''' docker ps --format '{{.Image}}' '''
		output = check_output(cmd, shell=True)
		racers = output.decode().count('racer')

		return int(racers)

	def reset_racer_latencies(self):

		self.racer_latencies = {}

		for i in range(1, self.number_of_racers + 1):
			self.racer_latencies[i] = []

master = Master()
master.start_new_lap()
		
