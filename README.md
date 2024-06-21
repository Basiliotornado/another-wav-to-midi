# another-wav-to-midi

#### prefer https://github.com/Basiliotornado/Dynamic-Midi-Converter

Welcome to my program :)
```
Flags: 
  -r R  Default: 8192  Fft bin size. Generally increases note count for small gain in lower notes, also increases processing time.
  -c C  Default: 32    Number of midi channels.
  -o O  Default: 0.75  Overlap between fft bins. Increases notes per second with higher numbers. range 0.0 to 0.99.
  -i                   Interpolate missing notes.
  -m                   If the input file is mono enable this flag.
```
Basically requires the soundfont to be used

Tuned for fluidsynth with chorus and reverb off. (if that changes anything?)
 
Example: https://youtu.be/sd0vAzpcplY
