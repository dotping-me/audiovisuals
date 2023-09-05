import matplotlib.pyplot as plt
import pygame
import time
import math
import vlc

class Audio :
	def __init__(self, path) :
		print(f"==={len(path) * '='}===\n   {path}\n==={len(path) * '='}===\n")

		self.path = path
		
		# Reads bytes and extracts header
		all_bytes	   = self._readAllBytes()
		file_header    = all_bytes[:4] # File header = 4 bytes = 32 bits = 0 to 3
		self.all_bytes = all_bytes[4:]

		# Processes file header
		# Bytes are in hex representaion -> Bit representation
		
		file_bits = ""
		for i in file_header :
			# Hex -> Denary -> Binary

			denary     = int(ord(i))
			binary	   = (str(bin(denary)))[2:]
			file_bits += binary + ((8 - len(binary)) * "0")

		# Associates bits with corresponding meanings. Stores only relevant data
		self.bit_rate = {
						"0000" : "Reserved", 
						"0001" : 32,
						"0010" : 40,
						"0011" : 48,
						"0100" : 56,
						"0101" : 64,
						"0110" : 80,
						"0111" : 96,
						"1000" : 112,
						"1001" : 128,
						"1010" : 160,
						"1011" : 192,
						"1100" : 224,
						"1101" : 256,
						"1110" : 320,
						"1111" : "Bad"
						}[file_bits[16 : 20]]

		# Gets frames of .mp3
		self.headers, self.datas = self._assembleFrames()

		# Calculates duration of .mp3
		self.duration = (len(self.all_bytes) * 8) / (self.bit_rate * 1024)

	def _readAllBytes(self) :
		"""
		Returns a list containing all bytes in the file
		"""

		all_bytes = []
		stopwatch = time.perf_counter()
		print(f"Reading | {self.path}")

		with open(self.path, "rb") as f :
			byte = f.read(1)

			# If not an empty byte (empty byte = EOF)
			while byte != b"" :
				all_bytes.append(byte)

				# Reads next byte
				byte = f.read(1)

		print(f"Read    | {len(all_bytes)} lines")
		print(f"\n[√√√] Processed in {round((time.perf_counter() - stopwatch), 2)} second(s) [√√√]\n")
		return all_bytes

	def _assembleFrames(self) :
		"""
		Returns headers and data frames in .mp3
		"""

		byte_pos   = 0
		start_head = False # Index of first read header byte
		start_data = False # Index of first read frame byte

		headers	= []
		datas	= []

		stopwatch = time.perf_counter()
		print(f"Assembling | Frames")

		while byte_pos < (len(self.all_bytes) - 1) :
			current_byte = self.all_bytes[byte_pos]
			next_byte	 = self.all_bytes[byte_pos + 1]

			# If current byte is a header byte
			if ("\\" in str(current_byte)) :

				# If it is the first read header byte of this frame
				if (not start_head) :
					start_head = byte_pos

				# Checks if next byte is a data byte
				if ("\\" not in str(next_byte)) :
					headers.append(self.all_bytes[start_head : byte_pos + 1])
					start_head = False

			# If current byte is a frame byte
			elif ("\\" not in str(current_byte)) :
				
				# If it is the first read data byte of this frame
				if (not start_data) :
					start_data = byte_pos

				# Checks if next byte is a header byte
				if ("\\" in str(next_byte)) :
					datas.append(self.all_bytes[start_data : byte_pos + 1])
					start_data = False

			# Reads next byte
			byte_pos += 1

		print(f"Headers    | {len(headers)}")
		print(f"Datas	   | {len(datas)}")
		print(f"\n[√√√] Processed in {round((time.perf_counter() - stopwatch), 2)} second(s) [√√√]\n")
		
		return (headers, datas)

	def filterFrames(self, valid_frames_only, avg_every_ms) :
		"""
		Changes data of frames according to parameters
		"""

		if valid_frames_only :
			mod_headers = []
			mod_datas   = []

		else :
			mod_headers = self.headers
			mod_datas   = self.datas

		stopwatch = time.perf_counter()
		print(f"Filtering | {len(self.headers)} frames\n")

		# Filters out invalid frames
		if valid_frames_only :
			print(f"Searching | Valid frames (0xFFF)")

			for i in range(len(self.headers)) : # Normally, len(self.headers) = len(self.datas)

				if len(self.headers[i]) > 1 :

					# Reads sync word
					first_8_bits = str(self.headers[i][0])
					next_4_bits  = str(self.headers[i][1])

					if (len(first_8_bits) == 7) and (len(next_4_bits) == 7) :
						sync_word = first_8_bits[4 : 6] + next_4_bits[4]

						# If sync word is valid, sync word = 1111 1111 1111 = 0xFFF
						if sync_word == "fff" :
							mod_headers.append(self.headers[i])
							mod_datas.append(self.datas[i])

			print(f"Found     | {len(mod_headers)} valid frames !\n")

		# Calculates new fps
		fps_for_mod = len(mod_datas) / self.duration
		f_time      = (self.duration / len(mod_datas)) * 1000 # Time for 1 frame in milliseconds
		f_in_x_ms   = int(avg_every_ms / f_time)

		# Averages data in all frames that play during x milliseconds interval
		# This preset values ae here in case avg_every_ms is False
		averaged 	= []
		fps_for_avg = False

		if avg_every_ms :
			print(f"Averaging | Every {avg_every_ms} millisecond(s) intervals")

			# Averages every f_in_x_ms frames
			frame_pos = 0

			# Pre-processes denary values
			vals = []
			for data in mod_datas :
				data = [ord(i) for i in data]
				vals.append(sum(data) // len(data))

			if f_in_x_ms >= 1 :
				while frame_pos < (len(vals) - int(f_in_x_ms)) :
					avg = sum(vals[frame_pos : frame_pos + f_in_x_ms]) // f_in_x_ms
					#avg = 20 * math.log10(avg // max(vals)) # Attempt to translate .mp3 to dB

					averaged.append(avg)

					frame_pos += f_in_x_ms

				# For leftover data
				if (len(vals) // f_in_x_ms) > len(averaged) :
					diff = len(vals) - len(averaged)

					# Appends leftover data
					for i in range(diff) :
						averaged.append(vals[-(i + 1)])

			else :
				averaged = vals

			# Calculates fps for averaged data in seconds
			fps_for_avg = len(averaged) / self.duration

			print(f"Averaged  | {len(averaged)} frames !")

		print(f"\n[√√√] Processed in {round((time.perf_counter() - stopwatch), 2)} second(s) [√√√]\n")
		return (
			{
			"headers" : mod_headers,
			"datas"   : mod_datas,
			"fps"     : fps_for_mod
			},

			{
			"headers" : mod_headers,
			"datas"   : averaged,
			"fps"	  : fps_for_avg
			}
			)

	def spectrograph(self, time_base, y_vals, show_graph) :
		"""
		Plots the spectrograph of .mp3
		"""

		# Set plot properties
		plt.title(self.path, loc = "left")
		stopwatch = time.perf_counter()

		plt.xlabel("Seconds")
		plt.ylabel("Values")

		plt.plot(time_base, y_vals)
		print(f"Plotting | {len(time_base)} x values")
		print(f"Plotting | {len(time_base)} y values")
		print(f"\n[√√√] Processed in {round((time.perf_counter() - stopwatch), 2)} second(s) [√√√]\n")

		if show_graph :
			plt.show()

class Visuals :
	def __init__(self, path_to_audio, valid_frames_only, avg_every_ms) :
		print(f"\n==={len(path_to_audio) * '='}===\n{((len(path_to_audio) // 2) - 2) * ' '}Visuals\n==={len(path_to_audio) * '='}===\n")

		# Sets up Audio object
		self.path_to_audio = path_to_audio
		self.audio 		   = Audio(path_to_audio)
		self.audio_data	   = self.audio.filterFrames(valid_frames_only, avg_every_ms)[1] # Hard-coded to work only with averaged values

	def startSim(self, window_settings, n_sim_points, cap_amplitude) : # window_settings = ((x, y), (r, g, b))
		"""
		Audio visualiser simulation

		Multiple points of mass are placed together to form a line. Gravity acts on every point so that they return to ground level (preset y value where gravity = 0)
		"""

		print(f"===============\n  Visualising\n===============\n")

		# Sets up window (main surface) and pygame vars
		pygame.init()
		pygame.display.set_caption(self.path_to_audio)

		self.window_size 	= window_settings[0]
		self.window_colours = window_settings[1]
		print(f"Window | Size    = {self.window_size}")
		print(f"Window | Colours = {self.window_colours}\n")

		clock   	  = pygame.time.Clock()
		print(f"FPS    | {int(self.audio_data['fps'])} frames per second\n")

		running 	  = True
		frame_reader  = 0

		# Sets up simulation points
		radii_preset = self.window_size[0] / (2 * n_sim_points)
		y_preset	 = int(0.8 * self.window_size[1])
		
		# Original coords
		self.sim_points_origin = [(int(radii_preset + (i * 2 * radii_preset)), y_preset) for i in range(n_sim_points)]

		self.sim_points = [Visuals.Point(int(radii_preset), (100, 200, 200), self.sim_points_origin[i][0], y_preset, 0) for i in range(n_sim_points)]
		sim_point_pos   = 0
		update_forces	= [None for _ in range(n_sim_points)]
		
		print(f"Points | {n_sim_points} points")
		print(f"Points | Radius  = {radii_preset} pixels")
		print(f"Points | Y-coord = {y_preset}")

		# Sets up y values
		if cap_amplitude :
			frame_y  = [(i % cap_amplitude) for i in self.audio_data["datas"]]

		else :
			frame_y = self.audio_data["datas"]

		# Finds max amplitude
		max_amplitude = max(frame_y)
		print(f"Points | Max Y   = {max_amplitude}")

		# Render main surface
		self.main_window = pygame.display.set_mode(self.window_size)
		stopwatch 		 = time.perf_counter()

		# To allow window to remain open when .mp3 finished and to have only one print statement of how much time it took
		one_time_prompt = True

		# Simulation loop
		while (running) :

			# Limits while loop iteration speed
			# Uses same fps as .mp3 so that simulation syncs up with audio
			clock.tick(int(self.audio_data["fps"]))

			# Event manager
			for event in pygame.event.get() :

				# If window is closed
				if event.type == pygame.QUIT :
					running = False

			if frame_reader < len(frame_y) :
				# Get value of byte at specific frame
				frame_data = frame_y[frame_reader]

				# Calculates forces and apply to point
				self.sim_points[sim_point_pos].dir = -1
				
				# Stores all data about movement of previous points
				update_forces[sim_point_pos] = (frame_data, max_amplitude, y_preset)

				# Updates points
				for i in range(n_sim_points) :
					if update_forces[i] :
						self.sim_points[i]._calcForces(update_forces[i][0], update_forces[i][1], update_forces[i][2])

			# If .mp3 finished playing
			else :
				if one_time_prompt :
					print(f"\n[√√√] Processed in {round((time.perf_counter() - stopwatch), 2)} second(s) [√√√]\n")
					one_time_prompt = False

				for i in self.sim_points :
					if i.y < y_preset :
						i.y += ((y_preset - i.y) / max_amplitude) * 50

					else :
						i.y = y_preset

			# Draws elements and updates display
			self._draw()
			pygame.display.update()

			# Reads next frame
			frame_reader  += 1
			sim_point_pos  = (sim_point_pos + 1) % n_sim_points

	def _draw(self) :
		"""
		Method to draw elements on screen
		"""

		# Fill in background
		self.main_window.fill(self.window_colours)

		"""
		# Draws points
		for i in self.sim_points :
			pygame.draw.circle(self.main_window, i.colour, (i.x, i.y), i.radius, 0)
		"""

		# Draws lines
		for i in range(len(self.sim_points)) :
			pygame.draw.line(self.main_window, self.sim_points[i].colour, self.sim_points_origin[i], (self.sim_points[i].x, self.sim_points[i].y), width = self.sim_points[i].radius)

	class Point :
		def __init__(self, radius, colour, x, y, direction) :

			# Sets up base values
			self.radius = radius
			self.colour = colour

			self.x   = x
			self.y   = y
			self.dir = direction

		def _calcForces(self, until_y, max_y, y_preset) :
			"""
			Calculates the acceleration per unit time (= displacement) of the force of gravity of the point at y
			"""
			
			# Calculates a ratio based on how high the point is
			# If it hasn't reach its destination and moving up
			
			if (self.dir == -1) :
				accel = ((until_y - self.y) / max_y) * 10
				self.y = int(self.y + accel)

				# if it reached its destination
				if int(self.y - until_y) <= 0 :

					# Change direction
					self.dir = 1

			# If it hasn't reach ground level and moving down
			elif (self.dir == 1) :
				accel  = ((y_preset - self.y) / max_y) * 10
				self.y = int(self.y + accel)

			# If at ground level
			else :
				accel 	 = 0
				self.dir = 0

if __name__ == "__main__" :
	"""
	# Class Audio testing !

	path  = "./audio/crimson-moon-sfx.mp3"
	audio = Audio(path)

	modded, averaged = audio.filterFrames(True, 100)

	fps   = averaged["fps"]
	spf   = fps ** -1
	datas = averaged["datas"]

	audio.spectrograph([(i * spf) for i in range(len(datas))], datas, True)
	"""

	""" Class Visuals testing ! """

	# Set up objects
	path 	 = "path-to-mp3"
	playback = vlc.MediaPlayer(path)
	visual   = Visuals(path, True, 1)

	# Plays .mp3
	playback.play()

	# Starts physics sim
	visual.startSim(((500, 500), (240, 240, 240)), 50, False)