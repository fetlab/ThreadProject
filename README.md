# ThreadProject
## Before you start
ExportThread.py is developed and tested in Windows. In MacOS, the script will probably not work. It is because that a part of the script trying to install numpy. Anyone is welcomed to fix the problem.

## Running on Mac OS
You need to have Numpy installed in the Fusion 360 Python interpreter. To do so:

* In Fusion, open View → Show Text Commands
* Make sure the radio button in the bottom-right corner is set to "Py"
* Run the following code:

```
import subprocess
print(subprocess.check_output([sys.executable, '-m', 'ensurepip', '--upgrade']).decode())
print(subprocess.check_output([sys.executable, '-m', 'pip', 'install', 'numpy']).decode())
```

* You may want to restart Fusion if your processer goes to 100%.

## How to set up ExportThread.py
### Autodesk Fuion 360
<ol>
  <li>Create a folder named ThreadProject in your computer. Recommended place is `C:/Users/YOUR_USERNAME/AppData/Roaming/Autodesk/Autodesk Fusion 360/API/Scripts/` (Windows). They are default folders for Fusion 360 scripts.</li>
  <li>Download and place ExportThread.py file under ThreadProject folder.</li>
  <li>Open Autodesk Fusion 360. Go to TOOLS tab then click the ADD-INS icon.</li>
  <li>Click the plus button next to My Scripts.</li>
  <li>Choose the ThreadProject folder you created.</li>
</ol>

### Slic3r
<ol>
  <li>Download and install Slic3r. https://slic3r.org/download/ We recommend to install under `C:\Program Files\` </li>
  <li>Note the installed folder.</li>
</ol>

## How to use ExportThread.py
<ol>
  <li>If there is no bodies called PrintBed and ThreadStartPoint, run ExportThread.py script by clicking TOOLS tab, ADD-INDS, ExportThread, and Run button. </li>
  <li>PrintBed and ThreadStartPoint bodies will be created. Click Cancel.</li>
  <li>Create main bodies, thread lines, and anchors on the PrintBed body. Main bodies will be embedding threads after print. Thread lines are paths that a thread will be placed. Anchors are to bend thread outside of main bodies. You do not need anchors for vertically bending thread. There should be an anchor wherever you want to change angle of the thread outside of main boides. Be careful to choose "New Bodies" option when you extrude from the PrintBed body. When creating threads, use sketch lines.</li>
  <li>(Important) Connect the beginning of the thread lines and the corner (-78mm, 0, 0) of the ThreadStartingPoint body by using 3D Sketch. You can create 3D Sketches by checking 3D Sketch option in SKETCH PALETTE while sketching.</li>
  <li>Run ExportThread.py script by clicking TOOLS tab, ADD-INDS, ExportThread, and Run button.</li>
  <li>Set File Path to tell where to export the result gcode files.</li>
  <li>Set Slic3r Path to tell where Slic3r-console.exe file is. The default is `C:\Program Files\Scli3r`.</li>
  <li>Choose main boides that will be embedding thread and used after print.</li>
  <li>Choose anchors and thread lines in order. First anchors and thread lines will be printed and placed first, and then second anchors and thread lines, and so on. When selecting thread lines, make sure they are chosen from the thread origin in order.</li>
</ol>
