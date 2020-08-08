# Copyright 2020 The DDSP Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file has been modified from the original

# Lint as: python3
"""Library of tensorboard summary functions relevant to DDSP training."""

import io

import spectral_ops
import core
import matplotlib.pyplot as plt
import numpy as np
import tensorflow.compat.v2 as tf


def fig_summary(tag, fig, step):
  """Writes an image summary from a string buffer of an mpl figure.

  This writer writes a scalar summary in V1 format using V2 API.

  Args:
    tag: An arbitrary tag name for this summary.
    fig: A matplotlib figure.
    step: The `int64` monotonic step variable, which defaults
      to `tf.compat.v1.train.get_global_step`.
  """
  buffer = io.BytesIO()
  fig.savefig(buffer, format='png')
  image_summary = tf.compat.v1.Summary.Image(
      encoded_image_string=buffer.getvalue())
  plt.close(fig)

  pb = tf.compat.v1.Summary()
  pb.value.add(tag=tag, image=image_summary)
  serialized = tf.convert_to_tensor(pb.SerializeToString())
  tf.summary.experimental.write_raw_pb(serialized, step=step, name=tag)


def waveform_summary(audio, audio_gen, step, name=''):
  """Creates a waveform plot summary for a batch of audio."""

  def plot_waveform(i, length=None, prefix='waveform', name=''):
    """Plots a waveforms."""
    waveform = np.squeeze(audio[i])
    waveform = waveform[:length] if length is not None else waveform
    waveform_gen = np.squeeze(audio_gen[i])
    waveform_gen = waveform_gen[:length] if length is not None else waveform_gen
    # Manually specify exact size of fig for tensorboard
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(2.5, 2.5))
    ax0.plot(waveform)
    ax1.plot(waveform_gen)

    # Format and save plot to image
    name = name + '_' if name else ''
    tag = f'waveform/{name}{prefix}_{i+1}'
    fig_summary(tag, fig, step)

  # Make plots at multiple lengths.
  batch_size = int(audio.shape[0])
  for i in range(batch_size):
    plot_waveform(i, length=None, prefix='full', name=name)
    plot_waveform(i, length=2000, prefix='125ms', name=name)


def get_spectrogram(audio, rotate=False, size=1024):
  """Compute logmag spectrogram."""
  mag = spectral_ops.compute_logmag(tf_float32(audio), size=size)
  if rotate:
    mag = np.rot90(mag)
  return mag


def spectrogram_summary(audio, audio_gen, step, name=''):
  """Writes a summary of spectrograms for a batch of images."""
  specgram = lambda a: spectral_ops.compute_logmag(tf_float32(a), size=768)

  # Batch spectrogram operations
  spectrograms = specgram(audio)
  spectrograms_gen = specgram(audio_gen)

  batch_size = int(audio.shape[0])
  for i in range(batch_size):
    # Manually specify exact size of fig for tensorboard
    fig, axs = plt.subplots(2, 1, figsize=(8, 8))

    ax = axs[0]
    spec = np.rot90(spectrograms[i])
    ax.matshow(spec, vmin=-5, vmax=1, aspect='auto', cmap=plt.cm.magma)
    ax.set_title('original')
    ax.set_xticks([])
    ax.set_yticks([])

    ax = axs[1]
    spec = np.rot90(spectrograms_gen[i])
    ax.matshow(spec, vmin=-5, vmax=1, aspect='auto', cmap=plt.cm.magma)
    ax.set_title('synthesized')
    ax.set_xticks([])
    ax.set_yticks([])

    # Format and save plot to image
    name = name + '_' if name else ''
    tag = f'spectrogram/{name}_{i+1}'
    fig_summary(tag, fig, step)


def audio_summary(audio, step, sample_rate=48000, name='audio'):
  """Update metrics dictionary given a batch of audio."""
  # Ensure there is a single channel dimension.
  batch_size = int(audio.shape[0])
  # remove below for STEREO
  if len(audio.shape) == 2:
    audio = audio[:, :, tf.newaxis]
  tf.summary.audio(
      name, audio, sample_rate, step, max_outputs=batch_size, encoding='wav')


def f0_summary(f0_hz, f0_hz_predict, step, name='f0_midi'):
  """Creates a plot comparison of ground truth f0_hz and predicted values."""
  batch_size = int(f0_hz.shape[0])

  # Resample predictions to match ground truth if they don't already.
  if f0_hz.shape[1] != f0_hz_predict.shape[1]:
    f0_hz_predict = core.resample(f0_hz_predict, f0_hz.shape[1])

  for i in range(batch_size):
    f0_midi = core.hz_to_midi(tf.squeeze(f0_hz[i]))
    f0_midi_predict = core.hz_to_midi(tf.squeeze(f0_hz_predict[i]))

    # Manually specify exact size of fig for tensorboard
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(6.0, 2.0))
    ax0.plot(f0_midi)
    ax0.plot(f0_midi_predict)
    ax0.set_title('original vs. predicted')

    ax1.plot(f0_midi_predict)
    ax1.set_title('predicted')

    # Format and save plot to image
    name = name + '_' if name else ''
    tag = f'f0_midi/{name}_{i + 1}'
    fig_summary(tag, fig, step)

def tf_float32(x):
  """Ensure array/tensor is a float32 tf.Tensor."""
  if isinstance(x, tf.Tensor):
    return tf.cast(x, dtype=tf.float32)  # This is a no-op if x is float32.
  else:
    return tf.convert_to_tensor(x, tf.float32)
