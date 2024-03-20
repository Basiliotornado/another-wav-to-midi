from scipy.signal import spectrogram, get_window
from scipy.io.wavfile import read
from numpy import rot90, flipud, log2, frombuffer
import mido
import argparse
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from subprocess import run
from sys import platform

parser = argparse.ArgumentParser(description='Generate a MIDI file from WAV')

parser.add_argument("-r",
                    type=int,
                    help="Fft bin size. Generally increases note count for small gain in lower notes, will increase processing time",
                    default=4096)
parser.add_argument("-c",
                    type=int,
                    help="Number of midi channels.",
                    default=32)
parser.add_argument("-o",
                    type=float,
                    help="Overlap between fft bins. Increases notes per second with higher numbers. range 0.01 to 0.99",
                    default=0.75)
parser.add_argument("-i",
                    type=str,
                    help="File name.")

args = parser.parse_args()

res = args.r
channels = args.c
overlap = args.o

if args.i: file = args.i
else: file = input("File name: ")
# im not sure what im doing

file_list = file.split(".")
file_name = "".join(file_list[:-1])
# if file_list[-1].lower() != "wav": # that's not how you check...
#     call(f"ffmpeg -i {file} {file_name}.wav",shell=True)

if file_list[-1].lower() != "wav":
    test = run(["ffmpeg",
                "-i", file,
                "-ar", "48000",
                "-c:v", "none",
                "-c:a", "pcm_s16le",
                "-f", "s16le",
                "-"], capture_output=True)
    wav = frombuffer(test.stdout, dtype="int16")
    data = wav.reshape((len(wav)//2,2))
    samplerate = 48000

else:
    samplerate, data = read(f"{file_name}.wav")

data2 = data[:,1]
data = data[:,0]

f, t, spectro = spectrogram(data, samplerate, window=get_window("hann", res), nperseg=res, noverlap=round(res*overlap), mode='psd')
_,_, spectro2 = spectrogram(data2, samplerate, window=get_window("hann", res), nperseg=res, noverlap=round(res*overlap), mode='psd')
specrot = flipud(rot90(spectro))
specrot2 = flipud(rot90(spectro2))
length = len(specrot)

keyFreq = {}
for freq in f:
    if freq == 0: continue
    keyFreq[int(freq)]=round(12 * log2(freq / 440) + 69)

def getkey(freq):
    if freq <= 0: return 0
    return keyFreq[int(freq)]

def interpolate(dct,x1,y1,x2,y2):
    tempindicies = list(range(x1+1,x2))
    for i in tempindicies:
        dct[i] = y1 + (i-x1) * ((y2-y1)/(x2-x1))



midi = mido.MidiFile(type = 1)

midi.ticks_per_beat = 5000

for i in range(channels):
    midi.tracks.append(mido.MidiTrack())

midi.tracks[0].append(mido.Message('control_change', channel = 0, control = 10, value = 0))
midi.tracks[0].append(mido.Message('control_change', channel = 1, control = 10, value = 127))

def red(column2):
    lst = {}
    notenum = 0
    tempvol = 0
    for value in column2:
        note = getkey(f[notenum])
        if note > 127: break
        notenum += 1
        if note < 0: continue
        if note != getkey(f[notenum]):
            lst[note] = (value + tempvol) ** 0.25
            tempvol = 0
        else:
            tempvol = (tempvol + value) * 0.8
    return lst

def reduceMulti(input):
    out = []

    if platform.startswith('linux'):
        with Pool(cpu_count()//2) as p:
            for result in tqdm(p.imap(red, input), desc = "Merging", total = len(input)):
                out.append(result)
    else:
        print("Multithreading is broken in windows! Please help troubleshoot!")
        for result in tqdm(map(red, input), desc = "Merging", total = len(input)):
            out.append(result)
  
    return out

specrot02 = reduceMulti(specrot)
specrot22 = reduceMulti(specrot2)
print()

large = 0
for column in specrot02:
    if max(column.values()) > large:
        large = max(column.values())
for column in specrot22:
    if max(column.values()) > large:
        large = max(column.values())

length = len(specrot02)

def interpolate2(list, length):
    tempspec = []
    for i in tqdm(range(length), desc = "Interpolating"):
        oldkey = 0
        olditem = 0
        tempspec.append({})
        for key,item in list[i].items():
            interpolate(tempspec[i],oldkey,olditem,key,item)
            tempspec[i][key] = item
            oldkey = key
            olditem = item
    return tempspec

#specrot02 = interpolate2(specrot02, length)
#specrot22 = interpolate2(specrot22, length)
print()

length = len(specrot02)
timer, wait = 0, 0

for column in tqdm(range(length), desc = "Writing midi"):
    wait = int(t[column]*10000 - timer)
    timer += wait
    note_list = [[0,0,0]]
    notenum = 0
    for note,value in specrot02[column].items():
        vel = int((value/large)*127)
        if vel<=1: continue #vel=0
        midi.tracks[0].append(mido.Message('note_on', channel = 0, note=int(note), velocity=vel))
        note_list.append([note, 0, 0])
        notenum += 1

    notenum = 0
    for note,value in specrot22[column].items():
        vel = int((value/large)*127)
        if vel<=1: continue #vel=0
        track = int(vel/(96/channels) + 1) #int(vel/16+1)
        #track = int(log2(vel/5+1))
        if track > channels-1: track = channels-1 # if track > 5: track = 5
        midi.tracks[track].append(mido.Message('note_on', channel = 1, note=int(note), velocity=vel))
        note_list.append([note, track, 1])
        notenum += 1

    for track in midi.tracks:
        track.append(mido.Message('note_off', channel = note_list[0][2], note=note_list[0][0], time = wait))
    note_list = note_list[1:]
    for play in note_list:
        midi.tracks[play[1]].append(mido.Message('note_off', channel = play[2], note=play[0]))

print("\n\nExporting")
midi.save(file_name + ".mid")
print("\n\nDone!")
