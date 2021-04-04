# Standard imports for core behaviour.
import os
import sys
import json
import spotipy
import webbrowser
import operator
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
import re
import random
# This is used for the actual handling and creation of images.
from PIL import Image, ImageDraw, ImageFilter, ImageFont
# This is the main Spotify API wrapper that we use to interface with Spotify.
import spotipy.util as util
# The following imports are all used for importing and exporting images.
import requests
from io import BytesIO
import base64
# The following imports are all used for analysing the colours in an image, and picking one out.
import binascii
import struct
import numpy as np
import scipy
import scipy.misc
import scipy.cluster
# This is used for converting colours back and forth between RGB and HSL, for adjustments.
import colorsys

# Check if the config file required exists.
if os.path.exists('config.json'):
	# Fetch data from the config file.
	with open('config.json') as config_file:
		config = json.load(config_file)
# If it doesn't, one needs making.
else:
	print("config.json is missing. See config_example.json from the repository to see how the file should be structured.")
	input("Press enter to exit.")
	exit()

print("Processing...")
	
# Fill in the app's details from the config file found above.
client_id = config['meta']['client_id']
client_secret = config['meta']['client_secret']
redirect_uri = config['meta']['redirect_uri']
controller_username = config['meta']['controller_username']

# Here are the preferred sizes and positions for the covers within the image.
cover_sizes = (230, 190, 150)
cover_positions = (25, 216), (195, 236), (325, 256)

# Method to get an auth token given a username and scope.
def get_auth_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri):
	try:
		token = util.prompt_for_user_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
	except:
		os.remove(f".cache-{username}")
		token = util.prompt_for_user_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

	return(token)

def create_playlist_image(playlist_id, month, title, covers, cover_sizes=cover_sizes, cover_positions=cover_positions):
	# This should always be the same, as it should be the number of both positions and sizes available, but to be sure...
	covers_to_use = len(covers)
	if len(cover_sizes) < covers_to_use:
		covers_to_use = len(cover_sizes)
	if len(cover_positions) < covers_to_use:
		covers_to_use = len(cover_positions)

	# First up, make an image to just sample colours from... It's alright if we distort the album covers a little in making this, as it will never be seen.
	colour_sample = Image.new('RGB', (150, 150), color=(255, 255, 255))

	# Loop through the covers and add one into an image.
	for i in range(covers_to_use):
		cover = covers[i]
		if cover != "":
			response = requests.get(cover)
			colour_sample_cover = Image.open(BytesIO(response.content))
			colour_sample_cover = colour_sample_cover.resize((150, 150))
			colour_sample.paste(colour_sample_cover)
			break

	# With our sample image pieced together, let's find some colours.
	# I'm not entirely clear on what all of this means, credit to Peter Hansen on Stack Overflow:
	# https://stackoverflow.com/questions/3241929/python-find-dominant-most-common-color-in-an-image

	# Transform the image into an array, and reshape it as suitable.
	array = np.asarray(colour_sample)
	shape = array.shape
	array = array.reshape(scipy.product(shape[:2]), shape[2]).astype(float)

	# Now, find clusters of colours within the image.
	codes, dist = scipy.cluster.vq.kmeans(array, 5)

	# Assign codes to our clusters and find occurrences.
	vectors, dist = scipy.cluster.vq.vq(array, codes)
	counts, bins = scipy.histogram(vectors, len(codes))

	# Find what was the most frequent.
	colour_index = scipy.argmax(counts)
	peak = codes[colour_index]

	# Convert our RGB values to HLS, so we can fiddle with the lightness.
	bg_red = peak[0]
	bg_green = peak[1]
	bg_blue = peak[2]
	fg_hue, fg_lightness, fg_saturation = colorsys.rgb_to_hls(bg_red, bg_green, bg_blue)
	# Move the hue around a third of the colour wheel for the foreground colour...
	fg_hue = (fg_hue + 255/3) % 255
	# And adjust the lightness, to make sure we don't just end up with the same colour.
	if fg_saturation < (255 * 0.3) and fg_lightness > (255 * 0.4) and fg_lightness < (255 * 0.6):
		if random.choice(range(2)) == 0:
			fg_lightness = 255
		else:
			fg_lightness = 0
	else:
		fg_lightness = 255 - fg_lightness
	fg_red, fg_green, fg_blue = colorsys.hls_to_rgb(fg_hue, fg_lightness, fg_saturation)

	# And now use those for our foreground and background colours.
	bg_colour = (int(bg_red), int(bg_green), int(bg_blue))
	fg_colour = (int(fg_red), int(fg_green), int(fg_blue))

	# Now let's move on to making our actual image.
	image = Image.new('RGB', (500, 500), color=bg_colour)

	month_font = ImageFont.truetype("C:/Windows/Fonts/ArialBD.ttf", 75)
	title_font = ImageFont.truetype("C:/Windows/Fonts/ArialBD.ttf", 39)

	month_text = ImageDraw.Draw(image)
	month_text.text((10, 10), month, fill=fg_colour, font=month_font)

	title_text = ImageDraw.Draw(image)
	title_text.text((10, 112), title, fill=fg_colour, font=title_font)

	# Now, loop through each of our covers.
	for i in range(covers_to_use):
		# We use covers_to_use - i - 1 for the index, because we want to work backwards through the images, so that number 1 appears on top of 2, on top of 3.
		index = covers_to_use - i - 1
		cover = covers[index]
		cover_size = cover_sizes[index]
		cover_position = cover_positions[index]
		cover_offset_x = 0
		cover_offset_y = 0
		# Make sure that we actually have a cover here to work with.
		if cover != "":
			response = requests.get(cover)
			cover_image = Image.open(BytesIO(response.content))
			# Figure out the image's new dimensions, in case it's not square... But let's hope that it is, to look a little nicer.
			width, height = cover_image.size
			if width > height:
				new_width = cover_size
				new_height = height / (width / cover_size)
				# Since the height is going to be smaller than expected, we'll offset the image a little bit, so that it's still centered as it should be.
				cover_offset_y = int((cover_size - new_height) / 2)
			elif height > width:
				new_width = width / (height / cover_size)
				new_height = cover_size
				# Since the width is going to be smaller than expected, we'll offset the image a little bit, so that it's still centered as it should be.
				cover_offset_x = int((cover_size - new_width) / 2)
			else:
				new_width = cover_size
				new_height = cover_size
			# And now go ahead and resize it to the established size.
			cover_image = cover_image.resize((int(new_width), int(new_height)))
			# Paste this cover in, in the specified place.
			image.paste(cover_image, (cover_position[0]+cover_offset_x, cover_position[1]+cover_offset_y))

	buffered = BytesIO()
	image.save(buffered, format="JPEG")
	return(base64.b64encode(buffered.getvalue()))

# Get the year and month that yesterday was, to reflect "the past month".
month = datetime.strftime(datetime.now() - timedelta(1), "%B")
year = datetime.strftime(datetime.now() - timedelta(1), "%Y")

# Get the auth token for the Monthly Music user. If they've not yet been authenticated in this app, this will open a web page to authenticate them.
controller_token = get_auth_token(controller_username, 'user-library-modify playlist-modify-public playlist-modify-private ugc-image-upload')

# Create our spotify object for the controller.
controller = spotipy.Spotify(auth=controller_token)
controller_id = controller.current_user()['id']

# Loop through each user listed in the config file.
for username in config['usernames']:
	# Get the auth token for this user. If they've not yet been authenticated in this app, this will open a web page to authenticate them.
	user_token = get_auth_token(username, 'user-top-read playlist-modify-public')

	# Create our spotify object for the user we're creating playlists for.
	user = spotipy.Spotify(auth=user_token)

	# Start piecing together a list of tracks to avoid recommending to the user.
	dont_recommend = []

	# Get the user's current top tracks.
	response = user.current_user_top_tracks(limit=50, time_range='short_term')
	tracks = response['items']
	# Form a list of just track IDs and images from this.
	top_track_ids = []
	top_track_images = []
	# Form a list of genres, counting the times they come up in the top tracks.
	top_genres = {}
	for track in tracks:
		top_track_ids.append(track['id'])
		if 'album' in track and 'images' in track['album'] and len(track['album']['images']) > 0:
				top_track_images.append(track['album']['images'][0]['url'])
		# Don't include any of the user's current top tracks as a recommended one for obvious reasons.
		# This uses the ISRC ID instead of Spotify's ID, so that it also avoids recommending different versions (i.e. from different markets) of the same tracks.
		dont_recommend.append(track['external_ids']['isrc'])
		for track_artist in track['artists']:
			artist = user.artist(track_artist['id'])
			for genre in artist['genres']:
				if genre not in top_genres.keys():
					genre_object = {}
					genre_object['name'] = genre
					genre_object['count'] = 0
					top_genres[genre] = (genre_object)
				top_genres[genre]['count'] = top_genres[genre]['count'] + 1

	# Get the various audio features of each of these tracks.
	features = user.audio_features(tracks=top_track_ids)
	# Now to sort the big array we have into more easily used arrays.
	danceability = []
	energy = []
	valence = []
	tempo = []
	for track_features in features:
		danceability.append(track_features['danceability'])
		energy.append(track_features['energy'])
		valence.append(track_features['valence'])
		tempo.append(track_features['tempo'])

	# Convert these into NumPy arrays, to get the percentile values from.
	danceability = np.array(danceability)
	energy = np.array(energy)
	valence = np.array(valence)
	tempo = np.array(tempo)
	# And now pick out the 25th and 75th percentiles from them.
	min_danceability = np.percentile(danceability, 25)
	max_danceability = np.percentile(danceability, 75)
	min_energy = np.percentile(energy, 25)
	max_energy = np.percentile(energy, 75)
	min_valence = np.percentile(valence, 25)
	max_valence = np.percentile(valence, 75)
	min_tempo = np.percentile(tempo, 25)
	max_tempo = np.percentile(tempo, 75)

	# Cut down the top genres to just the top 2, and just their names.
	recommender_genres = []
	for genre in top_genres.values():
		if len(recommender_genres) < 2:
			if len(recommender_genres) < 1:
				recommender_genres.append(genre['name'])
			elif genre['count'] > top_genres[recommender_genres[0]]['count']:
				recommender_genres.append(recommender_genres[0])
				recommender_genres[0] = genre['name']
			else:
				recommender_genres.append(genre['name'])
		elif genre['count'] > top_genres[recommender_genres[1]]['count']:
			if genre['count'] > top_genres[recommender_genres[0]]['count']:
				recommender_genres[1] = recommender_genres[0]
				recommender_genres[0] = genre['name']
			else:
				recommender_genres[1] = genre['name']

	# Now go through all of the user's playlists, so we know what else not to recommend.
	# Because this can only fetch up to 50 playlists at a time, and users might have more, the way that we handle this isn't particularly nice, but needs to be done...
	offset = 0
	all_found = False
	while not all_found:
		response = user.current_user_playlists(offset=offset)
		playlists = response['items']
		for playlist in playlists:
			response = user.playlist(playlist['id'])
			playlist_tracks = response['tracks']['items']
			for track in playlist_tracks:
				# Again, this uses the ISRC ID for the same reason as above... But only if it has it, since a playlist may include a user's local files.
				if track['track'] != None and 'isrc' in track['track']['external_ids'] and track['track']['external_ids']['isrc'] not in dont_recommend:
					dont_recommend.append(track['track']['external_ids']['isrc'])
		# If we found less than 50 playlists in this batch, we're done here.
		if len(playlists) < 50:
			all_found = True
		# Otherwise, move on to the next batch, using an offset.
		else:
			offset += 50
	# And let's do the same again, for the user's liked songs.

	# Trim the list of tracks down to the first 3, to get some recommendations based on.
	recommender_ids = top_track_ids[:3]
	
	recommendation_ids = []
	recommendation_images = []
	recommendation_attempts = 0
	
	# We'll try up to 5 times, to make sure that we have at least 25 recommendations.
	while len(recommendation_ids) < 25 and recommendation_attempts < 5:
		# The first three attempts, get some recommendations based on these 5 tracks and the min and max bands we found above.
		if recommendation_attempts < 3:
			response = user.recommendations(seed_tracks=recommender_ids, seed_genres=recommender_genres, limit=100, min_danceability=min_danceability, max_danceability=max_danceability, min_energy=min_energy, max_energy=max_energy, min_valence=min_valence, max_valence=max_valence, min_tempo=min_tempo, max_tempo=max_tempo)
		else:
			response = user.recommendations(seed_tracks=recommender_ids, seed_genres=recommender_genres, limit=100)
		
		recommendations = response['tracks']
			
		# And now build up a list of just the IDs and images from this list of recommendations.
		for recommendation in recommendations:
			if recommendation['external_ids']['isrc'] not in dont_recommend:
				recommendation_ids.append(recommendation['id'])
				if 'album' in recommendation and 'images' in recommendation['album'] and len(recommendation['album']['images']) > 0:
						recommendation_images.append(recommendation['album']['images'][0]['url'])
						
		# Cut it down to unique values.
		recommendation_ids = list(set(recommendation_ids))
		recommendation_images = list(set(recommendation_images))
		
		recommendation_attempts += 1

	# Get the user's details (specifically their name).
	user_display_name = user.current_user()['display_name']

	# Create the Top Tracks playlist for this user.
	playlist = controller.user_playlist_create(controller_id, month+'\'s Top Tracks', False, user_display_name+'\'s top tracks for '+month+' '+year+'.')
	playlist_id = playlist.get('id')

	# Add their top tracks into the playlist.
	controller.user_playlist_add_tracks(controller_id, playlist_id, top_track_ids)

	# Create an image for the playlist and assign it.
	playlist_image = create_playlist_image(playlist_id, month, "Top Tracks", top_track_images[:3])
	controller.playlist_upload_cover_image(playlist_id, playlist_image)

	# Follow the top tracks playlist, for the user.
	user.user_playlist_follow_playlist(controller_id, playlist_id)
	
	# Only deal with recommendations if we actually have any...
	if len(recommendation_ids) > 0:
		# Create the Recommended Tracks playlist.
		playlist = controller.user_playlist_create(controller_id, month+'\'s Recommended Tracks', False, user_display_name+'\'s recommended tracks for '+month+' '+year+'.')
		playlist_id = playlist.get('id')

		# Add their recommended tracks into the playlist.
		controller.user_playlist_add_tracks(controller_id, playlist_id, recommendation_ids[:50])

		# Create an image for the playlist and assign it.
		playlist_image = create_playlist_image(playlist_id, month, "Recommended Tracks", recommendation_images[:3])
		controller.playlist_upload_cover_image(playlist_id, playlist_image)

		# Follow the recommended tracks playlist, for the user.
		user.user_playlist_follow_playlist(controller_id, playlist_id)

print("Done!")
input("Press enter to exit.")
exit()
