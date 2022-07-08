from scipy.signal import spectrogram, get_window
from scipy.io.wavfile import read
from numpy import rot90, flipud, log2, log, append
import mido
import argparse

def getkey(freq):
    if freq <= 0: return 0
    return int(12 * log2(freq / 440) + 69)
    
def interpolate(dct,x1,y1,x2,y2):
    tempindicies = list(range(x1+1,x2))
    for i in tempindicies:
        dct[i] = y1 + (i-x1) * ((y2-y1)/(x2-x1))
    
res = 4096
div = 0.8

parser = argparse.ArgumentParser(description='Generate a MIDI file from WAV')

parser.add_argument("-r", type=int,
                    help="Generally increases note count for small gain in lower notes, will increase processing time")
parser.add_argument("-d", type=float,
                    help="Increases notes per second with higher numbers. range 0.01 to 0.99")
parser.add_argument("-f", type=str,
                    help="File name ")

args = parser.parse_args()

if args.r: res = args.r
if args.d: div = args.d
if args.f: file = args.f
else: file = input("File name: ")
# im not sure what im doing

samplerate, data = read(file + ".wav")
data = data[:,0] # remove if audio file is mono


f, t, spectro = spectrogram(data, samplerate, window=get_window("hann", res), nperseg=res, noverlap=round(res*div), mode='magnitude')
specrot = flipud(rot90(spectro))

timestop = t[1]-t[0]

length = len(specrot)

specrot2 = []

midi = mido.MidiFile(type = 1)
for i in range(7):
    midi.tracks.append(mido.MidiTrack())


print("\n\nReducing notes\n--------------")
counter = 0
for column2 in specrot:
    lst = {}
    notenum = 0
    tempvol = 0
    for value2 in column2:
        note = getkey(f[notenum])
        if note > 127: break
        notenum += 1
        if note < 0: continue
        if note != getkey(f[notenum]): 
            lst[note] = value2+tempvol
            tempvol = 0
        else:
            tempvol = (tempvol+value2)*0.85
        
    specrot2.append(lst)
    
    print(round(counter/length,3), end = "\r")
    counter += 1

length = len(specrot2)
print("\n\nInterpolating\n--------------")
tempspec = []
for i in range(len(specrot2)):
    oldkey = 0
    olditem = 0
    tempspec.append({})
    for key,item in specrot2[i].items():
        interpolate(tempspec[i],oldkey,olditem,key,item)
        tempspec[i][key] = item
        oldkey = key
        olditem = item
    print(round(i/length,2), end = "\r") #how do i make it not put 1.09 lol

specrot2 = tempspec
del tempspec

large = 0
for column in specrot2:
    if max(column.values()) > large:
        large = max(column.values())

length = len(specrot2)
dif1, dif2, counter = 0, 0, 0

print("\n\nPlacing notes\n--------------")
for column in specrot2:
    notenum = 0
    note_list = [[0,0]]
    wait = int(dif1-dif2)
    dif1 += timestop*1000
    dif2 += wait
    for note,value in column.items():
        c = int((value/large)*127)
        track = int(log(c+1)*2)
        if track > 6: track = 6
        midi.tracks[track].append(mido.Message('note_on', note=int(note), velocity=c))
        note_list.append([note, track])

        notenum += 1

    for track in midi.tracks:
        track.append(mido.Message('note_off', note=note_list[0][0], time = wait))
        note_list = note_list[1:]
    for play in note_list:
        midi.tracks[play[1]].append(mido.Message('note_off', note=play[0]))
    print(round(counter/length,2), end = "\r") #how do i make it not put 1.09 lol
    counter += 1
print("\n\nExporting")
midi.save(file + ".mid")
print("\n\nDone!")
