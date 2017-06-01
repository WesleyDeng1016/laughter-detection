import numpy as np
import scipy.signal as signal
import os
import sys
import librosa
from python_speech_features import mfcc
from python_speech_features import delta
import keras
from keras.models import load_model

import compute_features

def frame_to_time(frame_index):
	return(frame/100.)

def seconds_to_frames(s):
	return(int(s*100))

def collapse_to_start_and_end_frame(instance_list):
    return (instance_list[0], instance_list[-1])

def frame_span_to_time_span(frame_span):
    return (frame_span[0] / 100., frame_span[1] / 100.)

def seconds_to_samples(s,sr):
    return s*sr

def format_features(mfcc_feat, delta_feat,index):
    return np.append(mfcc_feat[index-window_size:index+window_size],delta_feat[index-window_size:index+window_size])

def cut_laughter_segments(instance_list,y,sr):
	new_audio = []
	for start, end in instance_list:
		sample_start = int(seconds_to_samples(start,sr))
		sample_end = int(seconds_to_samples(end,sr))
		clip = y[sample_start:sample_end]
		new_audio = np.concatenate([new_audio,clip])
	return new_audio

def get_instances_from_rows(rows):
	return [(float(row.split(' ')[1]),float(row.split(' ')[2])) for row in rows]

def lowpass(sig, filter_order = 2, cutoff = 0.01):
	#Set up Butterworth filter
	filter_order  = 2
	B, A = signal.butter(filter_order, cutoff, output='ba')

	#Apply the filter
	return(signal.filtfilt(B,A, sig))

def get_laughter_instances(probs, threshold = 0.5, min_length = 20):
	instances = []
	current_list = []
	for i in xrange(len(probs)):
		if np.min(probs[i:i+1]) > threshold:
			current_list.append(i)
		else:
			if len(current_list) > 0:
				instances.append(current_list)
				current_list = []

	instances = [frame_span_to_time_span(collapse_to_start_and_end_frame(i)) for i in instances if len(i) > min_length]
	return instances

def parse_inputs():
	process = True

	try:
		a_file = sys.argv[1]
	except:
		print "Enter the audio file path as the first argument"
		process = False

	try:
		model_path = sys.argv[2]
	except:
		print "Enter the stored model path as the second argument"
		process = False

	try:
		output_audio_path = sys.argv[3]
	except:
		print "Enter the output audio path as the third argument"
		process = False

	try:
		threshold = float(sys.argv[4])
	except:
		threshold= 0.5

	try:
		min_length = float(sys.argv[5])
	except:
		min_length = 0.2

	if process:
		return (a_file, model_path, output_audio_path, threshold, min_length)
	else:
		return False




# Usage: python segment_laughter.py <input_audio_file> <stored_model_path> <output_audio_path>

if __name__ == '__main__':
	if parse_inputs():
		a_file, model_path, output_audio_path, threshold, min_length = parse_inputs()
		min_length = seconds_to_frames(min_length)

		print
		print "Loading audio file..."
		y,sr = librosa.load(a_file,sr=8000)
		full_res_y, full_res_sr = librosa.load(a_file,sr=44100)

		model = load_model(model_path)
		window_size = 37

		mfcc_feat = compute_features.compute_mfcc_features(y,sr)
		delta_feat = compute_features.compute_delta_features(mfcc_feat)

		zero_pad = np.zeros((window_size,mfcc_feat.shape[1]))
		padded_mfcc_feat = np.vstack([zero_pad,mfcc_feat,zero_pad])
		padded_delta_feat = np.vstack([zero_pad,delta_feat,zero_pad])

		feature_list = []
		for i in range(window_size, len(mfcc_feat) + window_size):
			feature_list.append(format_features(padded_mfcc_feat, padded_delta_feat, i))
		feature_list = np.array(feature_list)

		print
		print "Looking for laughter..."
		probs = model.predict_proba(feature_list).reshape((len(mfcc_feat),))
		filtered = lowpass(probs)

		instances = get_laughter_instances(filtered, threshold=threshold, min_length=min_length)
                maxv = np.iinfo(np.int16).max

                if os.path.isdir(output_audio_path):
                    for index, instance in enumerate(instances):
                        laughs = cut_laughter_segments([instance],full_res_y,full_res_sr)
                        librosa.output.write_wav(output_audio_path + "/laugh_" + str(index) + ".wav", (laughs * maxv).astype(np.int16), full_res_sr)

                else:
                    laughs = cut_laughter_segments(instances,full_res_y,full_res_sr)
                    librosa.output.write_wav(output_audio_path, (laughs * maxv).astype(np.int16), full_res_sr)

		print
		print
		print "Wrote laughter to file: %s" % (output_audio_path)
		print
		print "Laughter Segments: "
		print instances
		print
