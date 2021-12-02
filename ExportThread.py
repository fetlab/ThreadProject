#Author-Hyunyoung Kim
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback
import subprocess
import cmath, math
import sys, os, platform
import inspect

#Use the below three lines if you get error "ModuleNotFoundError: No module named 'numpy'". They may not work on Mac.
# import subprocess
# subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
# import numpy as np

try:
    import numpy as np
except ModuleNotFoundError:
    message = """
Can't import Numpy. You probably need to install it. To do so:
* In Fusion, open View → Show Text Commands
* Make sure the radio button in the bottom-right corner is set to "Py"
* Run the following code:

    import subprocess
    print(subprocess.check_output([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip']).decode())
    print(subprocess.check_output([sys.executable, '-m', 'pip', 'install', 'numpy']).decode())

* You may want to restart Fusion if your processor goes to 100%.
* Try to run this script again."""
    sys.exit(-1)

script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
script_name = os.path.splitext(os.path.basename(script_path))[0]
script_dir = os.path.dirname(script_path)

sys.path.append(os.path.join(script_dir, "Modules"))
try:
    import numpy as np
finally:
    del sys.path[-1]


_app = adsk.core.Application.cast(None)
_ui = adsk.core.UserInterface.cast(None)
_handlers = []
_inputs = adsk.core.CommandInputs.cast(None)

_handlers = []
_selectedLines = []
_selecedBodies = []
_selectedAnchors = []
if platform.system() == 'Windows':
    _filePath = "C:\Program Files\Slic3r"
    _slic3rPath = "C:\Program Files\Slic3r\\"
    _slic3rExe = 'slic3r-console'
elif platform.system() == 'Darwin':
    _filePath = '/tmp'
    _slic3rPath = '/Applications/Slic3r.app/Contents/MacOS'
    _slic3rExe = 'Slic3r'

# Print settings
_layerThickness = 0.2
_bedSizeX = 79        ##TODO Currently set for 79 x 235 mm.
_bedSizeOriginalX = 235
_threadOriginX = -(_bedSizeOriginalX/2 - _bedSizeX/2)
_bedSizeY = 235
_temperature = 200
_bedTemperature = 60

# To combine three g-code files
# _threadZPoints = [0.0]

# Thread coordinates
_lines = []

# Keep track of selected anchors and thread lines
_numOfLinesAndAnchors = 20


def run(context):
    ui = None
    try:
        global _app, _ui
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Create the command definition. 
        cmdDef = _ui.commandDefinitions.itemById('rhapso')
        if not cmdDef:
            cmdDef = _ui.commandDefinitions.addButtonDefinition('rhapso','Rhapso','User interface for Thread-embedding 3D Printer')

        # # Connect to the command destroyed event.
        # onDestroy = MyCommandDestroyHandler()
        # cmdDef.destroy.add(onDestroy)
        # _handlers.append(onDestroy)

        # # Connect to the input changed event.           
        # onInputChanged = MyCommandInputChangedHandler()
        # cmdDef.inputChanged.add(onInputChanged)
        # _handlers.append(onInputChanged)    

        # Connect to the command created event.
        onCommandCreated = MyCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        # Create print bed body.
        createPrintBedAndThreadOriginBodies()
        
        # Execue the command definition.
        cmdDef.execute()
        
        # Prevent this module from being terminated when the script returns, because we are waiting for event handlers to fire.
        adsk.autoTerminate(False)

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def createPrintBedAndThreadOriginBodies():
    try:
        design = adsk.fusion.Design.cast(_app.activeProduct)
        root = design.rootComponent
        
        ### 1. Check if there is a body called "PrintBed".
        bodyPrintBed = root.bRepBodies.itemByName("PrintBed")

        if bodyPrintBed is None:
            ### 2. Draw sketch lines, path.
            sketches = root.sketches
            sketch = sketches.add(root.xYConstructionPlane)
            lines = sketch.sketchCurves.sketchLines
            recLines = lines.addTwoPointRectangle(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(_bedSizeX/10, _bedSizeY/10, 0))

            ### 3. Extrude
            extrudes = root.features.extrudeFeatures
            prof = sketch.profiles.item(0)
            distance = adsk.core.ValueInput.createByReal(-0.5)
            extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

            ### 4. Get the print bed body
            body = extrude.bodies.item(0)
            body.name = "PrintBed"

        #######################################
        ### Do the same with the starting point of thread
        ### 1. Check if there is a body called "ThreadStartingPoint"
        bodyThreadPoint = root.bRepBodies.itemByName("ThreadStartingPoint")

        if bodyThreadPoint is None:
            ### 2. Draw sketch lines, path.
            sketches = root.sketches
            sketch = sketches.add(root.xYConstructionPlane)
            lines = sketch.sketchCurves.sketchLines
            recLines = lines.addTwoPointRectangle(adsk.core.Point3D.create(_threadOriginX/10, 0, 0), adsk.core.Point3D.create(_threadOriginX/10-0.5, -0.5, 0))

            ### 3. Extrude
            extrudes = root.features.extrudeFeatures
            prof = sketch.profiles.item(0)
            distance = adsk.core.ValueInput.createByReal(-0.5)
            extrude = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

            ### 4. Get the print bed body
            body = extrude.bodies.item(0)
            body.name = "ThreadStartingPoint"

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# From https://forums.autodesk.com/t5/fusion-360-api-and-scripts/python-api-export-stl-from-brepbody-fails/td-p/6299830
def exportCompBodyAsSTL():
    try:
        product = _app.activeProduct
        design = adsk.fusion.Design.cast(product)
        root = design.rootComponent
        exportMgr = design.exportManager
        outDir = "C:\Program Files\Slic3r"

        for comp in design.allComponents:
            if comp != root:
                # Find any occurrence using this component.
                occs = root.allOccurrencesByComponent(comp)
                if occs.count > 0:
                    occ = occs.item(0)
                    
            for body in comp.bRepBodies:
                if comp != root:
                    # Create a body proxy.
                    body = body.createForAssemblyContext(occ)

                fileName = os.path.join(outDir, comp.name.replace(" ","_" ) + body.name)

                # create stl exportOptions
                stlExportOptions = exportMgr.createSTLExportOptions(body, fileName)
                stlExportOptions.sendToPrintUtility = False
                stlExportOptions.isBinaryFormat = False
                
                exportMgr.execute(stlExportOptions)

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))



# Event handler for the commandCreated event.
class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try: 
            global _inputs

            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # # Connect to the command destroyed event.     # Remove for Add-in
            onDestroy = MyCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Connect to command excute handler. 
            onExecute = MyExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # Connect to the input changed event.           
            # onInputChanged = MyCommandInputChangedHandler()
            # cmd.inputChanged.add(onInputChanged)
            # _handlers.append(onInputChanged)    

            # onSelect = MySelectHandler()
            # cmd.select.add(onSelect)
            # _handlers.append(onSelect) 
            
            # onUnSelect = MyUnSelectHandler()
            # cmd.unselect.add(onUnSelect)            
            # handlers.append(onUnSelect) 
            
            # Get the CommandInputs collection associated with the command.
            _inputs = cmd.commandInputs
            #inputs = cmd.commandInputs
            
            # Connect to command inputs.
            des = adsk.fusion.Design.cast(_app.activeProduct)
            um = des.unitsManager       # TODO. change the unit.

            # File path
            filePathInput = _inputs.addStringValueInput('strFilePath', 'File Path', _filePath)

            #Slic3r path
            slic3rPathInput = _inputs.addStringValueInput('strSlic3rPath', 'Slic3r Path', _slic3rPath)

            # Print body selector
            modelInput = _inputs.addSelectionInput('selBody', 'Select 3D Models', 'Select bodies to 3D print')
            modelInput.addSelectionFilter(adsk.core.SelectionCommandInput.SolidBodies) # Ref https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-03033DE6-AD8E-46B3-B4E6-DADA8D389E4E
            #modelInput.setSelectionLimits(1)
            modelInput.setSelectionLimits(0)

            # # Create group
            groupCmdInput = _inputs.addGroupCommandInput('group', 'Thread lines and anchors')
            groupCmdInput.isExpanded = True
            groupChildInputs = groupCmdInput.children
            
            # Thread selector
            for i in range(_numOfLinesAndAnchors):
                anchorInput = groupChildInputs.addSelectionInput('selAnchor'+str(i), 'Select Anchors', 'Select bodies to to anchor thread')
                anchorInput.addSelectionFilter(adsk.core.SelectionCommandInput.SolidBodies)
                anchorInput.setSelectionLimits(0)

                threadInput = groupChildInputs.addSelectionInput('selThread'+str(i), 'Select Thread Lines', 'Select sketchlines to export as thread. The first line should be connected to the thread origin. The lines should be connected.')
                #threadInput.addSelectionFilter(adsk.core.SelectionCommandInput.Edges)
                threadInput.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
                threadInput.setSelectionLimits(0)

            # # Anchor body selector
            # modelInput = _inputs.addSelectionInput('selAnchor', 'Select Anchors', 'Select bodies to to anchor thread')
            # modelInput.addSelectionFilter(adsk.core.SelectionCommandInput.SolidBodies)
            # modelInput.setSelectionLimits(0)


        except:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MyExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            adsk.core.EventArgs = adsk.core.CommandEventArgs.cast(args)

            selBody = _inputs.itemById('selBody')
            selBody = adsk.core.SelectionCommandInput.cast(selBody)
            for i in range(0, selBody.selectionCount):
                body = adsk.fusion.BRepBody.cast(selBody.selection(i).entity)
                _selecedBodies.append(body)
            

            for i in range(_numOfLinesAndAnchors):
                selThread = _inputs.itemById('selThread'+str(i))
                selThread = adsk.core.SelectionCommandInput.cast(selThread)
                for j in range(0, selThread.selectionCount):
                    line = adsk.fusion.SketchLine.cast(selThread.selection(j).entity)
                    _selectedLines.append(line)
                if _selectedLines[-1] != None:
                    _selectedLines.append(None)

            for i in range(_numOfLinesAndAnchors):
                selAnchor = _inputs.itemById('selAnchor'+str(i))
                selAnchor = adsk.core.SelectionCommandInput.cast(selAnchor)
                for j in range(0, selAnchor.selectionCount):
                    anchor = adsk.fusion.BRepBody.cast(selAnchor.selection(j).entity)
                    _selectedAnchors.append(anchor)
                if _selectedAnchors[-1] != None:
                    _selectedAnchors.append(None)

            exportThread()
            exportBody()
            exportAnchor()
            exportAll()

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def exportThread():
    try:
        global _lines

        _lines = np.zeros((len(_selectedLines), 2, 3))
        
        #ui.messageBox(str(lines))
        for i in range(0, len(_selectedLines)):
            if _selectedLines[i] != None:
                #TODO: Remove below if. I don't accept BRepEdge anymore.
                if _selectedLines[i].classType() == "adsk::fusion::BRepEdge":
                    edge = adsk.fusion.BRepEdge.cast(_selectedLines[i]) 
                    startPoint = edge.startVertex.geometry   # Point3D type
                    endPoint = edge.endVertex.geometry
                else:
                    edge = adsk.fusion.SketchLine.cast(_selectedLines[i]) # "adsk::fusion::SketchLine"
                    startPoint = edge.worldGeometry.startPoint
                    endPoint = edge.worldGeometry.endPoint
            
                _lines[i][0] = [round(startPoint.x*10, 4), round(startPoint.y*10, 4), round(startPoint.z*10, 4)]
                _lines[i][1] = [round(endPoint.x*10, 4), round(endPoint.y*10, 4), round(endPoint.z*10, 4)]
            else:
                _lines[i] = None


        # ##############################
        # ### 1. Order lines from the origin ver. 1
        
        # #TODO: handle the case when the lines are not connected or are not connected the thread origin.

        # tmpIndex = np.where((_lines[:,:,0] == _threadOriginX) & (_lines[:,:,1] == 0) & (_lines[:,:,2] == 0))

        # _lines[[tmpIndex[0][0], 0]] = _lines[[0, tmpIndex[0][0]]]     # Move origin to the first row
        # _lines[0, [0, tmpIndex[1][0]]] = _lines[0, [tmpIndex[1][0], 0]]          # Move origin to the first column


        # # Sort lines from the origin.
        # for i in range(1, len(_lines)):
        #     tmpIndex = np.where((_lines[i:,:,0] == _lines[i-1, 1, 0]) & (_lines[i:,:,1] == _lines[i-1, 1, 1]) & (_lines[i:,:,2] == _lines[i-1, 1, 2]))

        #     if i < len(_lines) - 1:

        #         _lines[[tmpIndex[0][0], i]] = _lines[[i, tmpIndex[0][0]]]     # Move the line to the current row
        #     _lines[i, [0, tmpIndex[1][0]]] = _lines[i, [tmpIndex[1][0], 0]]                         # Move the point of the line that is connected to the previous line to the first column
        
        # _lines[:,:,0] = _lines[:,:,0] - _threadOriginX      # Shift x points to the center of the ring.

        # # fThread.write(str(_lines))
        # # _ui.messageBox(str(_lines))

        ##############################
        ### 1. Order lines from the origin ver. 2
        
        #TODO: handle the case when the lines are not connected to the thread origin or not chosen in the right order.Z

        # _ui.messageBox(str(_lines))

        if (_lines[0,0,0] != _threadOriginX) or (_lines[0,0,1] != 0) or (_lines[0,0,2] != 0):
            #Assume the first line is connected to the origin. Move origin to the first column
            tmp = _lines[0,0]
            _lines[0,0] = _lines[0,1]
            _lines[0,1] = tmp

        # Sort lines from the origin.
        for i in range(1, len(_lines)):
            if not np.isnan(_lines[i,0,0]):
                if not np.isnan(_lines[i-1,0,0]):
                    if (_lines[i,0,0] != _lines[i-1,1,0]) or (_lines[i,0,1] != _lines[i-1,1,1]) or (_lines[i,0,2] != _lines[i-1,1,2]):
                        tmp = _lines[i,0]
                        _lines[i,0] = _lines[i,1]
                        _lines[i,1] = tmp

                elif not np.isnan(_lines[i-2,0,0]):
                    if (_lines[i,0,0] != _lines[i-2,1,0]) or (_lines[i,0,1] != _lines[i-2,1,1]) or (_lines[i,0,2] != _lines[i-2,1,2]):
                        tmp = _lines[i,0]
                        _lines[i,0] = _lines[i,1]
                        _lines[i,1] = tmp
        
        # _ui.messageBox(str(_lines))

        _lines[:,:,0] = _lines[:,:,0] - _threadOriginX      # Shift x points to the center of the ring.

        # fThread.write(str(_lines))
        # _ui.messageBox(str(_lines))


        ##############################
        ### 2. Conver thread geometry to g-code

        h = _bedSizeOriginalX/2 # Center point of the ring in mm
        r = 100 # Radius of the ring in mm
        stepsPCircle = 142.5
        theta = math.radians(-90)
        
        # fThread.write('\n\nT1 ; change tool to Extruder 2\n')

        # 2. project the position on the ring. If there are anchors on the way, (1) lift the ring up, (2) go to the position (slightly outer than the anchor), (3) go to the position
        preEValue = 0
        
        fThread = open(os.path.join(_filePath, "output-thread-tmp.gcode"), "w")
        fThread.write(';anchor\n')

        for i in range(len(_lines)):
            if not np.isnan(_lines[i,0,0]):
                startPoint = _lines[i][0]
                endPoint = _lines[i][1]
                
                x1 = startPoint[0]
                y1 = startPoint[1]
                z1 = startPoint[2]
                x2 = endPoint[0]
                y2 = endPoint[1]
                z2 = endPoint[2]

                if x2 != x1:
                    la = (y2-y1)/(x2-x1)     # a for linear formulat y = ax + b
                    lb = - la*x1 + y1         # b for linear formulat y = ax + b
                    qa = 1 + pow(la,2)        #a for quadratic formula    ax^2 + bx + c = 0
                    qb = 2*la*(lb-h) - 2*h    #b for quadratic formula    ax^2 + bx + c = 0
                    qc = pow(lb-h,2) + pow(h,2) - pow(r, 2)
                    spoolPoint1x = (-qb-cmath.sqrt(pow(qb,2) - 4*qa*qc))/(2*qa) 
                    spoolPoint1y = la*spoolPoint1x + lb
                    spoolPoint2x = (-qb+cmath.sqrt(pow(qb,2) - 4*qa*qc))/(2*qa)
                    spoolPoint2y = la*spoolPoint2x + lb
                    
                else:                  
                    qa = 1               # linear formula x = x1
                    qb = - 2 * h
                    qc = pow(h, 2) + pow (x1 - h, 2) - pow(r, 2)
                    spoolPoint1y = (-qb-cmath.sqrt(pow(qb,2) - 4*qa*qc))/(2*qa)
                    spoolPoint1x = x1
                    spoolPoint2y = (-qb+cmath.sqrt(pow(qb,2) - 4*qa*qc))/(2*qa)
                    spoolPoint2x = x1

                # Remove imajinary numbers
                spoolPoint1x = spoolPoint1x.real
                spoolPoint1y = spoolPoint1y.real
                spoolPoint2x = spoolPoint2x.real
                spoolPoint2y = spoolPoint2y.real
                
                # fThread.write(';Spool points: (({},{}),({},{}))\n'.format(spoolPoint1x, spoolPoint1y, spoolPoint2x, spoolPoint2y))

                # Choose a target spool point further from the startPoint
                d1 = pow(spoolPoint1x-x1, 2) + pow(spoolPoint1y-y1, 2)
                d2 = pow(spoolPoint2x-x1, 2) + pow(spoolPoint2y-y1, 2)
                if d1 > d2:
                    tSpoolPointx = spoolPoint1x
                    tSpoolPointy = spoolPoint1y
                else:
                    tSpoolPointx = spoolPoint2x
                    tSpoolPointy = spoolPoint2y

                # Get spool point z
                if x2 != x1:
                    lza = (z2-z1)/(x2-x1)     # a for linear formulat z = ax + b
                    lzb = - lza*x1 + z1 
                    tSpoolPointz = lza * tSpoolPointx + lzb
                else:
                    lza = (z2-z1)/(y2-y1)     # a for linear formulat z = ax + b
                    lzb = - lza*y1 + z1 
                    tSpoolPointz = lza * tSpoolPointy + lzb

                # Get target theta
                tTheta = cmath.atan((tSpoolPointy-h)/(tSpoolPointx-h)).real
                if tSpoolPointx-h < 0:
                    tTheta = tTheta + cmath.pi            # add 90 degress if the target point is on the left side of the ring.


                # fThread.write(';Target spool points: ({},{})\n'.format(tSpoolPointx, tSpoolPointy))
                
                # Convert spool xy point to the rotation of the ring
                # Get rotational direction to get to the target spool point


                dTheta = tTheta - theta
                # fThread.write(';Theta, tTheta, dTheta: ({},{},{})\n'.format(math.degrees(theta), math.degrees(tTheta), math.degrees(dTheta)))
                

                #_ui.messageBox("dTheta: {}".format(math.degrees(abs(dTheta))))
                eValue = dTheta / (2 * cmath.pi) * stepsPCircle      # -1 is to inverse the angle. + is to rotate the ring clockwise and - is for anticlockwise
                # _ui.messageBox("steps: {}".format(eValue))

                if z1 != z2:
                    fThread.write('G0 Y%.5f ; Move bed to the center\n' % (_bedSizeY/2))    # put print bed at the center.
                
                fThread.write("G1 E{:.5f} Z{:.5f} F800\n".format(eValue-preEValue, tSpoolPointz))
                fThread.write("G92 E0\n")
                
                if z1 != z2 and i != 0:
                    fThread.write('G92 E0 ; set the current filament position to E2=0\n') # Assume 12 o'clock is E2=0
                    preEValue = eValue

                #TODO: check if preEValue works well. I need to put thread in another layer to test this.
                    
                theta = tTheta

            elif np.isnan(_lines[i,0,0]) and i != len(_lines)-1:
                # Add comment for anchor
                # Add gcode lines to over-rotate the ring. Thread can be fixed during print this way. Currently rotate 30 degree of the ring.
                if eValue-preEValue >= 0:
                    fThread.write('G0 Y117.50000 ; Move bed to the center\n')
                    fThread.write('G1 E12 F800\n')
                    fThread.write('G92 E0\n')
                    fThread.write(';anchor\n')
                    fThread.write('G1 E-12 F800\n')
                    fThread.write('G92 E0\n')

                else:
                    fThread.write('G0 Y117.50000 ; Move bed to the center\n')
                    fThread.write('G1 E-12 F800\n')
                    fThread.write('G92 E0\n')
                    fThread.write(';anchor\n')
                    fThread.write('G1 E12 F800\n')
                    fThread.write('G92 E0\n')



        # fThread.write('G92 E0 ; set the current filament position to E2=0\n')

        # fThread.write('T0 ; change back to normal extruder')
        fThread.close()


    except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def exportBody():
    try:
        product = _app.activeProduct
        design = adsk.fusion.Design.cast(product)
        exportMgr = design.exportManager

        #####################################
        # 1. Export each body to a stl file
        for body in _selecedBodies:
            fileName = os.path.join(_filePath, body.name)

            # create stl exportOptions
            stlExportOptions = exportMgr.createSTLExportOptions(body, fileName)
            stlExportOptions.sendToPrintUtility = False
            stlExportOptions.isBinaryFormat = False
            
            exportMgr.execute(stlExportOptions)


        #####################################
        # 2. Combine all stl files into one file.
        f_all = open(_filePath +"/body-all.stl", "w")
        f_all.write("solid ASCII\n")

        for body in _selecedBodies:
            f = open(os.path.join(_filePath, body.name + ".stl"), "r")
            count = f.readlines()
            # _ui.messageBox(str(type(count)))
            for i in range(1, len(count)-1):
                f_all.write(count[i])

        f_all.write("endsolid")
        f_all.close()


        #####################################
        # 3. Make a g-code file
        result = subprocess.check_output([os.path.join(_slic3rPath, _slic3rExe),
        os.path.join(_filePath, "body-all.stl"),
        "--first-layer-height", str(_layerThickness),
        "--layer-height",str(_layerThickness),
        "--temperature", str(_temperature),
        "--bed-temperature", str(_bedTemperature),
        "--filament-diameter","1.75",
        "--nozzle-diameter","0.4",
        "--skirts", "0",
        "--dont-arrange",
        "-o", os.path.join(_filePath, "output-body.gcode")]) 


        #####################################
        # 4. Clean the g-code file
        fBody = open(_filePath +"/output-body.gcode", "r")
        fBodyLines = fBody.readlines()
        fBody.close()

        # 4.1 Remove header and footer lines
        layerChangeIndexesBody = [i for i, lA in enumerate(fBodyLines) if lA.startswith('G1 Z')] 

        # 4.1.1 move the initial X,Y positions after the first G1 Z... line
        if fBodyLines[layerChangeIndexesBody[1]-1].startswith('G1 X'):
            fBodyLines.insert(layerChangeIndexesBody[1]+1, fBodyLines[layerChangeIndexesBody[1]-1])

        # 4.1.2 Remove header. Lines before the second 'G1 Z...' and two lines after that. 'G1 E-2.00000 F2400.00000' and 'G92 E0'
        del fBodyLines[:layerChangeIndexesBody[1]]
        layerChangeIndexesBody = [i for i, lA in enumerate(fBodyLines) if lA.startswith('G1 Z')]
        del fBodyLines[layerChangeIndexesBody[0]+1]
        del fBodyLines[layerChangeIndexesBody[0]+1]

        # 4.1.3 remove footer. Lines after the last 'G92 E0'
        endOfPrintIndexAnchor = [i for i, lA in enumerate(fBodyLines) if lA.startswith('G92 E0')]
        del fBodyLines[endOfPrintIndexAnchor[-1]+1:]

        # 4.2 Copy M106 or M107 from the nearest previous line to set fan speed.
        layerChangeIndexesBody = [i for i, lA in enumerate(fBodyLines) if lA.startswith('G1 Z')]
        
        fBodyLines.insert(layerChangeIndexesBody[0]+1, "M107\n") # First layer is always M107
        layerChangeIndexesBody[1:] = [x + 1 for x in layerChangeIndexesBody[1:]] 
        
        for i in range(1, len(layerChangeIndexesBody)):
            for j in range(layerChangeIndexesBody[i]-1, layerChangeIndexesBody[i-1], -1):
                if fBodyLines[j].startswith('M106') or fBodyLines[j].startswith('M107'):
                    fBodyLines.insert(layerChangeIndexesBody[i]+1, fBodyLines[j])
                    layerChangeIndexesBody[i+1:] = [x + 1 for x in layerChangeIndexesBody[i+1:]] 
                    break

        # 4.3 Put 'G1 X... Y... F...' at i+2th line
        for i in range(1, len(layerChangeIndexesBody)):
            # 4.3.1 Move 'G1 X... Y... F...' to i+2th line if they are in next 2-4 lines
            if fBodyLines[layerChangeIndexesBody[i]+2].startswith('G1 X') and (fBodyLines[layerChangeIndexesBody[i]+2].find('F') != -1):
                pass

            elif fBodyLines[layerChangeIndexesBody[i]+3].startswith('G1 X') and (fBodyLines[layerChangeIndexesBody[i]+3].find('F') != -1):
                fBodyLines.insert(layerChangeIndexesBody[i]+2, fBodyLines[layerChangeIndexesBody[i]+3])
                del fBodyLines[layerChangeIndexesBody[i]+4]
                
            elif fBodyLines[layerChangeIndexesBody[i]+4].startswith('G1 X') and (fBodyLines[layerChangeIndexesBody[i]+4].find('F') != -1):
                fBodyLines.insert(layerChangeIndexesBody[i]+2, fBodyLines[layerChangeIndexesBody[i]+4])
                del fBodyLines[layerChangeIndexesBody[i]+5]

            # 4.3.2 Copy X,Y points from the nearest previous line if there is no G1 X... Y... F7800 in next 2-4 lines
            else:
                for j in range(layerChangeIndexesBody[i]-1, layerChangeIndexesBody[i-1], -1):
                    if fBodyLines[j].startswith('G1 X') and fBodyLines[j].startswith('F') != -1:
                        fBodyLines.insert(layerChangeIndexesBody[i]+2, fBodyLines[j])
                        layerChangeIndexesBody[i+1:] = [x + 1 for x in layerChangeIndexesBody[i+1:]] 

                        # Remove the previous X,Y coordinates to remove unnecessary movement at the end of the previous layer
                        del fBodyLines[j]
                        layerChangeIndexesBody[i:] = [x - 1 for x in layerChangeIndexesBody[i:]] 
                        break

                    elif fBodyLines[j].startswith('G1 X') and fBodyLines[j].startswith('E') != -1:
                        strXY, sep, tail = fBodyLines[j].partition('E')       # strXY = 'G1 X... Y... '
                        fBodyLines.insert(layerChangeIndexesBody[i]+2, strXY+'F7800.000')
                        layerChangeIndexesBody[i+1:] = [x + 1 for x in layerChangeIndexesBody[i+1:]] 
                        break

                    elif fBodyLines[j].startswith('G1 X'):
                        _ui.messageBox('Error!')
                        break

            # 4.4 Reset E values after every layer change
        for i in range(1, len(layerChangeIndexesBody)):
            # 4.4.1 If there is 'G91 E0' at 4th line after 'G1 Z...', Move that line and the previous line above 'G1 Z...'
            if fBodyLines[layerChangeIndexesBody[i]+4].startswith('G92 E0'):
                fBodyLines.insert(layerChangeIndexesBody[i], fBodyLines[layerChangeIndexesBody[i]+3])
                del fBodyLines[layerChangeIndexesBody[i]+4]
                fBodyLines.insert(layerChangeIndexesBody[i]+1, fBodyLines[layerChangeIndexesBody[i]+4])
                del fBodyLines[layerChangeIndexesBody[i]+5]
                layerChangeIndexesBody[i] = layerChangeIndexesBody[i]+2

            # 4.4.2 If there is no 'G91 E0' before 'G1 Z...', Reset E value until meeting the next 'G92 E0'
            elif not fBodyLines[layerChangeIndexesBody[i]-1].startswith('G92 E0'):
                # 3.4.2.1 Insert 'G92 E0' before layer change
                offset = 0
                prevEValue = -1
                while True:
                    offset += 1
                    if fBodyLines[layerChangeIndexesBody[i]-offset].find('E') != -1:
                        if fBodyLines[layerChangeIndexesBody[i]-offset].find('F') != -1:
                            _ui.messageBox('Error!')
                        else:
                            head, sep, eValueStr = fBodyLines[layerChangeIndexesBody[i]-offset].partition('E')
                            prevEValue = float(eValueStr.strip())
                            fBodyLines.insert(layerChangeIndexesBody[i], "G1 E"+str(round(prevEValue-2, 5))+" F2400.000\n") # Retract
                            fBodyLines.insert(layerChangeIndexesBody[i]+1, "G92 E0\n")
                            fBodyLines.insert(layerChangeIndexesBody[i]+5, "G1 E2.00000 F2400.000\n")
                            
                            layerChangeIndexesBody[i] = layerChangeIndexesBody[i]+2
                            layerChangeIndexesBody[i+1:] = [x + 3 for x in layerChangeIndexesBody[i+1:]] 

                        break
                
                # 4.4.2.1 Shift E values until meeting the next 'G92 E0'
                eValueDiff = prevEValue - 2
                offset = 3
                while True:
                    offset += 1
                    if fBodyLines[layerChangeIndexesBody[i]+offset].startswith('G92 E0'):
                        break
                    elif fBodyLines[layerChangeIndexesBody[i]+offset].startswith('G1 X') and fBodyLines[layerChangeIndexesBody[i]+offset].find('E') != -1: #G1 X26.295 Y147.794 E75.48784
                        head, sep, strEValue = fBodyLines[layerChangeIndexesBody[i]+offset].partition('E')
                        newEValue = float(strEValue.strip()) - eValueDiff
                        fBodyLines[layerChangeIndexesBody[i]+offset] = head + sep + "%.5f\n" % newEValue
                    elif fBodyLines[layerChangeIndexesBody[i]+offset].startswith('G1 E') and fBodyLines[layerChangeIndexesBody[i]+offset].find('F') != -1: #G1 E88.29126 F2400.00000
                        head, sepE, tail = fBodyLines[layerChangeIndexesBody[i]+offset].partition('E')
                        strEValue, sepF, tailF = tail.partition('F')
                        newEValue = float(strEValue.strip()) - eValueDiff
                        fBodyLines[layerChangeIndexesBody[i]+offset] = head + sepE + ("%.5f " % newEValue) + sepF + tailF

        ### 5. Add layer number before each G1 Z...
        layerChangeIndexesBody = [i for i, lA in enumerate(fBodyLines) if lA.startswith('G1 Z')]
        fBodyLines.insert(0, ';LAYER:1 ;BODY\n')
        layerChangeIndexesBody = [x+1 for x in layerChangeIndexesBody]
        for i in range(1, len(layerChangeIndexesBody)):
            fBodyLines.insert(layerChangeIndexesBody[i], ';LAYER:'+str(i+1)+' ;BODY\n')
            layerChangeIndexesBody[i+1:] = [x+1 for x in layerChangeIndexesBody[i+1:]]

        fAnchorTmp = open(_filePath +"/output-body-tmp.gcode", "w")
        fAnchorTmp.writelines(fBodyLines)
        fAnchorTmp.close()


    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def exportAnchor():
    try:
        product = _app.activeProduct
        design = adsk.fusion.Design.cast(product)
        exportMgr = design.exportManager

        #####################################
        # 1. Export each body to a stl file and then gcode file
        for i in range(len(_selectedAnchors)):
            if _selectedAnchors[i] is not None:
                fileName = os.path.join(_filePath, "anchor" + str(i))

                # create stl exportOptions
                stlExportOptions = exportMgr.createSTLExportOptions(_selectedAnchors[i], fileName)
                stlExportOptions.sendToPrintUtility = False
                stlExportOptions.isBinaryFormat = False
                
                exportMgr.execute(stlExportOptions)

                result = subprocess.check_output([os.path.join(_slic3rPath, _slic3rExe),
                os.path.join(_filePath, "anchor" + str(i) + ".stl"),
                "--first-layer-height", str(_layerThickness),
                "--layer-height",str(_layerThickness),
                "--temperature", str(_temperature),
                "--bed-temperature", str(_bedTemperature),
                "--filament-diameter","1.75",
                "--nozzle-diameter","0.4",
                "--skirts", "0",
                "--dont-arrange",
                "-o", os.path.join(_filePath, "output-anchor" + str(i) + ".gcode")]) 


        #####################################
        ### 2. Combine until thread line
        ### 2.1 Check height of thread. Visit one of two points of all thread, and then make a list of height. Skip z=0.
        threadHeights = []
        threadHeightIndexes = []
        for i in range(len(_lines)):
            if not np.isnan(_lines[i,0,0]):
                if _lines[i, 0, 2] != 0 and (len(threadHeights) == 0 or threadHeights[-1] != _lines[i, 0, 2]):
                    threadHeights.append(_lines[i, 0, 2])        #Do not save 0
                    threadHeightIndexes.append(i)
        #TODO: threadHeightIndexes is never used in this function. Check if this block of code is necessary.


        ### 2.2 Read all anchor gcode files
        allfAnchorlines = []
        for i in range(len(_selectedAnchors)):
            if _selectedAnchors[i] is not None:
                fAnchor = open(os.path.join(_filePath, "output-anchor" + str(i) + ".gcode"), "r")
                fAnchorLines = fAnchor.readlines()
                allfAnchorlines.append(fAnchorLines)
                fAnchor.close()
            else:
                allfAnchorlines.append(None)

        
        #####################################
        ### 3. Clean gcode files. Remove header and footer lines. Insert code resetting E value if none
        # newAllfAnchorLines = list (allfAnchorlines)
        for k in range(len(allfAnchorlines)):
            if allfAnchorlines[k] is not None:

                ### 3.1 Remove header and footer lines
                layerChangeIndexesAnchor = [i for i, lA in enumerate(allfAnchorlines[k]) if lA.startswith('G1 Z')] 

                ### 3.1.1 move the initial X,Y positions after the first G1 Z... line
                if allfAnchorlines[k][layerChangeIndexesAnchor[1]-1].startswith('G1 X'):
                    allfAnchorlines[k].insert(layerChangeIndexesAnchor[1]+1, allfAnchorlines[k][layerChangeIndexesAnchor[1]-1])

                ### 3.1.2 Remove header. Lines before the second 'G1 Z...' and two lines after that. 'G1 E-2.00000 F2400.00000' and 'G92 E0'
                del allfAnchorlines[k][:layerChangeIndexesAnchor[1]]
                layerChangeIndexesAnchor = [i for i, lA in enumerate(allfAnchorlines[k]) if lA.startswith('G1 Z')]
                del allfAnchorlines[k][layerChangeIndexesAnchor[0]+1]
                del allfAnchorlines[k][layerChangeIndexesAnchor[0]+1]

                ### 3.1.3 remove footer. Lines after the last 'G92 E0'
                endOfPrintIndexAnchor = [i for i, lA in enumerate(allfAnchorlines[k]) if lA.startswith('G92 E0')]
                del allfAnchorlines[k][endOfPrintIndexAnchor[-1]+1:]

                ### 3.2 Copy M106 or M107 from the nearest previous line to set fan speed.
                layerChangeIndexesAnchor = [i for i, lA in enumerate(allfAnchorlines[k]) if lA.startswith('G1 Z')]
                
                allfAnchorlines[k].insert(layerChangeIndexesAnchor[0]+1, "M107\n") # First layer is always M107
                layerChangeIndexesAnchor[1:] = [x + 1 for x in layerChangeIndexesAnchor[1:]] 
                
                for i in range(1, len(layerChangeIndexesAnchor)):
                    for j in range(layerChangeIndexesAnchor[i]-1, layerChangeIndexesAnchor[i-1], -1):
                        if allfAnchorlines[k][j].startswith('M106') or allfAnchorlines[k][j].startswith('M107'):
                            allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+1, allfAnchorlines[k][j])
                            layerChangeIndexesAnchor[i+1:] = [x + 1 for x in layerChangeIndexesAnchor[i+1:]] 
                            break

                ### 3.3 Put 'G1 X... Y... F...' at i+2th line
                for i in range(1, len(layerChangeIndexesAnchor)):
                    ### 3.3.1 Move 'G1 X... Y... F...' to i+2th line if they are in next 2-4 lines
                    if allfAnchorlines[k][layerChangeIndexesAnchor[i]+2].startswith('G1 X') and (allfAnchorlines[k][layerChangeIndexesAnchor[i]+2].find('F') != -1):
                        pass

                    elif allfAnchorlines[k][layerChangeIndexesAnchor[i]+3].startswith('G1 X') and (allfAnchorlines[k][layerChangeIndexesAnchor[i]+3].find('F') != -1):
                        allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+2, allfAnchorlines[k][layerChangeIndexesAnchor[i]+3])
                        del allfAnchorlines[k][layerChangeIndexesAnchor[i]+4]
                        
                    elif allfAnchorlines[k][layerChangeIndexesAnchor[i]+4].startswith('G1 X') and (allfAnchorlines[k][layerChangeIndexesAnchor[i]+4].find('F') != -1):
                        allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+2, allfAnchorlines[k][layerChangeIndexesAnchor[i]+4])
                        del allfAnchorlines[k][layerChangeIndexesAnchor[i]+5]

                    ### 3.3.2 Copy X,Y points from the nearest previous line if there is no G1 X... Y... F7800 in next 2-4 lines
                    # if ((not (allfAnchorlines[k][layerChangeIndexesAnchor[i]+2].startswith('G1 X') and allfAnchorlines[k][layerChangeIndexesAnchor[i]+2].find('F') != -1)) and 
                    # (not (allfAnchorlines[k][layerChangeIndexesAnchor[i]+3].startswith('G1 X') and allfAnchorlines[k][layerChangeIndexesAnchor[i]+3].find('F') != -1)) and 
                    # (not (allfAnchorlines[k][layerChangeIndexesAnchor[i]+4].startswith('G1 X') and allfAnchorlines[k][layerChangeIndexesAnchor[i]+4].find('F') != -1))):
                    else:
                        for j in range(layerChangeIndexesAnchor[i]-1, layerChangeIndexesAnchor[i-1], -1):
                            if allfAnchorlines[k][j].startswith('G1 X') and allfAnchorlines[k][j].startswith('F') != -1:
                                allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+2, allfAnchorlines[k][j])
                                layerChangeIndexesAnchor[i+1:] = [x + 1 for x in layerChangeIndexesAnchor[i+1:]] 

                                # Remove the previous X,Y coordinates to remove unnecessary movement at the end of the previous layer
                                del allfAnchorlines[k][j]
                                layerChangeIndexesAnchor[i:] = [x - 1 for x in layerChangeIndexesAnchor[i:]] 
                                break

                            elif allfAnchorlines[k][j].startswith('G1 X') and allfAnchorlines[k][j].startswith('E') != -1:
                                strXY, sep, tail = allfAnchorlines[k][j].partition('E')       # strXY = 'G1 X... Y... '
                                allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+2, strXY+'F7800.000')
                                layerChangeIndexesAnchor[i+1:] = [x + 1 for x in layerChangeIndexesAnchor[i+1:]] 
                                break

                            elif allfAnchorlines[k][j].startswith('G1 X'):
                                _ui.messageBox('Error!')
                                break
                    

                ### 3.4 Reset E values after every layer change
                for i in range(1, len(layerChangeIndexesAnchor)):
                    # 3.4.1 If there is 'G91 E0' at 4th line after 'G1 Z...', Move that line and the previous line above 'G1 Z...'
                    if allfAnchorlines[k][layerChangeIndexesAnchor[i]+4].startswith('G92 E0'):
                        allfAnchorlines[k].insert(layerChangeIndexesAnchor[i], allfAnchorlines[k][layerChangeIndexesAnchor[i]+3])
                        del allfAnchorlines[k][layerChangeIndexesAnchor[i]+4]
                        allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+1, allfAnchorlines[k][layerChangeIndexesAnchor[i]+4])
                        del allfAnchorlines[k][layerChangeIndexesAnchor[i]+5]
                        layerChangeIndexesAnchor[i] = layerChangeIndexesAnchor[i]+2

                    # 3.4.2 If there is no 'G91 E0' before 'G1 Z...', Reset E value until meeting the next 'G92 E0'
                    elif not allfAnchorlines[k][layerChangeIndexesAnchor[i]-1].startswith('G92 E0'):
                        # 3.4.2.1 Insert 'G92 E0' before layer change
                        offset = 0
                        prevEValue = -1
                        while True:
                            offset += 1
                            if allfAnchorlines[k][layerChangeIndexesAnchor[i]-offset].find('E') != -1:
                                if allfAnchorlines[k][layerChangeIndexesAnchor[i]-offset].find('F') != -1:
                                    _ui.messageBox('Error!')
                                else:
                                    head, sep, eValueStr = allfAnchorlines[k][layerChangeIndexesAnchor[i]-offset].partition('E')
                                    prevEValue = float(eValueStr.strip())
                                    allfAnchorlines[k].insert(layerChangeIndexesAnchor[i], "G1 E"+str(round(prevEValue-2, 5))+" F2400.000\n") # Retract
                                    allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+1, "G92 E0\n")
                                    allfAnchorlines[k].insert(layerChangeIndexesAnchor[i]+5, "G1 E2.00000 F2400.000\n")
                                    
                                    layerChangeIndexesAnchor[i] = layerChangeIndexesAnchor[i]+2
                                    layerChangeIndexesAnchor[i+1:] = [x + 3 for x in layerChangeIndexesAnchor[i+1:]] 

                                break
                        
                        # 3.4.2.1 Shift E values until meeting the next 'G92 E0'
                        eValueDiff = prevEValue - 2
                        offset = 3
                        while True:
                            offset += 1
                            if allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].startswith('G92 E0'):
                                break
                            elif allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].startswith('G1 X') and allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].find('E') != -1: #G1 X26.295 Y147.794 E75.48784
                                head, sep, strEValue = allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].partition('E')
                                newEValue = float(strEValue.strip()) - eValueDiff
                                allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset] = head + sep + "%.5f\n" % newEValue
                            elif allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].startswith('G1 E') and allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].find('F') != -1: #G1 E88.29126 F2400.00000
                                head, sepE, tail = allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset].partition('E')
                                strEValue, sepF, tailF = tail.partition('F')
                                newEValue = float(strEValue.strip()) - eValueDiff
                                allfAnchorlines[k][layerChangeIndexesAnchor[i]+offset] = head + sepE + ("%.5f " % newEValue) + sepF + tailF

                ### 4. Add layer number before each G1 Z...
                layerChangeIndexesAnchor = [i for i, lA in enumerate(allfAnchorlines[k]) if lA.startswith('G1 Z')]
                allfAnchorlines[k].insert(0, ';LAYER:1 ;ANCHOR'+str(k)+'\n')
                layerChangeIndexesAnchor = [x+1 for x in layerChangeIndexesAnchor]
                for i in range(1, len(layerChangeIndexesAnchor)):
                    allfAnchorlines[k].insert(layerChangeIndexesAnchor[i], ';LAYER:'+str(i+1)+' ;ANCHOR'+str(k)+'\n')
                    layerChangeIndexesAnchor[i+1:] = [x+1 for x in layerChangeIndexesAnchor[i+1:]]
            
                fAnchorTmp = open(_filePath +"/output-anchor"+str(k)+"-tmp.gcode", "w")
                fAnchorTmp.writelines(allfAnchorlines[k])
                fAnchorTmp.close()
        

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def exportAll():
    try:
        fThread = open(os.path.join(_filePath, "output-thread-tmp.gcode"), "r")
        fBody = open(os.path.join(_filePath, "output-body-tmp.gcode"), "r")
        fAll  = open(os.path.join(_filePath, "output-all.gcode"), "w")

        # Read body, anchor, thread files
        fBodyLines = fBody.readlines()
        allfAnchorlines = []
        for i in range(len(_selectedAnchors)):
            if _selectedAnchors[i] is not None:
                fAnchor = open(os.path.join(_filePath, "output-anchor" + str(i) + "-tmp.gcode"), "r")
                fAnchorLines = fAnchor.readlines()
                allfAnchorlines.append(fAnchorLines)
                fAnchor.close()
            else:
                allfAnchorlines.append(None)
        fThreadLines = fThread.readlines()

        # Add header
        fAll.write(";Header\n")
        fAll.write("M107\n")
        fAll.write("M104 S200 ; set temperature\n")
        fAll.write("G28 ; home all axes\n")
        fAll.write("G1 Z5 F5000 ; lift nozzle\n\n")        
        fAll.write("; Filament gcode\n\n")

        fAll.write("M109 S200 ; set temperature and wait for it to be reached\n")
        fAll.write("G21 ; set units to millimeters\n")
        fAll.write("G90 ; use absolute coordinates\n")
        fAll.write("M82 ; use absolute distances for extrusion\n")
        fAll.write("G92 E0\n\n")
        fAll.write(";End of header\n")

        ##############################
        ### 1. Check height of thread. Visit one of two points of all thread, and then make a list of height. Skip z=0.
        threadHeights = []
        threadHeightIndexes = []
        for i in range(len(_lines)):
            if (not np.isnan(_lines[i,0,0])) and _lines[i, 0, 2] != 0 and (len(threadHeights) == 0 or threadHeights[-1] != _lines[i, 0, 2]):
                threadHeights.append(_lines[i, 0, 2])        #Do not save 0
                threadHeightIndexes.append(i)

        ##############################
        ### 2. Get indexes of layer change lines
        ### 2.1 For body gcode file
        layerChangeIndexesBody = [i for i, lA in enumerate(fBodyLines) if lA.startswith(';LAYER:')]
        ### 2.2 For anchor gcode files
        allLayerChangeIndexesAnchor = []
        for k in range(len(allfAnchorlines)):
            if allfAnchorlines[k] is not None:
                layerChangeIndexesAnchor = [i for i, lA in enumerate(allfAnchorlines[k]) if lA.startswith(';LAYER:')]
                allLayerChangeIndexesAnchor.append(layerChangeIndexesAnchor)
            else:
                allLayerChangeIndexesAnchor.append(None)       
        ### 2.3 For Thread gcode file
        threadPauseIndexes =  [i for i, lA in enumerate(fThreadLines) if lA.startswith(';anchor')]
        # _ui.messageBox(str(placeToPutAnchorLines))
        
        ##############################
        ### 3. Combine body, anchor, thread gcode files
        prevThreadLayerIndex = 0
        fAll.write("T0\n")      # Say below code is for Extruder 1

        ### 3.1 Add body & anchor lines until the thread height
        threadLayer = int(threadHeights[0] / _layerThickness)
        layerAfterThread = 0
        for i in range(0, threadLayer + 1):
            ### 3.1.1 Add body g-code until the thread layer
            if i < len(layerChangeIndexesBody) - 1:
                fAll.writelines(fBodyLines[layerChangeIndexesBody[i]:layerChangeIndexesBody[i+1]-1])
            elif i == len(layerChangeIndexesBody) - 1:  # when i is last layer, copy until the end of the file
                fAll.writelines(fBodyLines[layerChangeIndexesBody[i]:-1])
            
            ### 3.1.2 Add anchor g-code until the thread layer
            for k in range(len(allfAnchorlines)):
                if allfAnchorlines[k] is not None:
                    if i < len(allLayerChangeIndexesAnchor[k]) - 1:
                        fAll.writelines(allfAnchorlines[k][allLayerChangeIndexesAnchor[k][i]:allLayerChangeIndexesAnchor[k][i+1]-1])
                    elif i == len(allLayerChangeIndexesAnchor[k]) - 1:  # when i is last layer, copy until the end of the file
                        fAll.writelines(allfAnchorlines[k][allLayerChangeIndexesAnchor[k][i]:-1])
            layerAfterThread = i
        
        ##############################
        ### 4. Add anchor gcode until the end and add thread
        layerAfterThread += 1
        threadCounter = 0
        for k in range(len(allfAnchorlines)): 
            if allfAnchorlines[k] is not None:
                fAll.writelines(allfAnchorlines[k][allLayerChangeIndexesAnchor[k][layerAfterThread]:-1])
            else: #TODO write thread lines
                fAll.write("T1 ;Thread\n")
                if threadCounter < len(threadPauseIndexes) - 1:
                    fAll.writelines(fThreadLines[threadPauseIndexes[threadCounter]+1:threadPauseIndexes[threadCounter+1]])
                elif threadCounter == len(threadPauseIndexes) - 1:
                    fAll.writelines(fThreadLines[threadPauseIndexes[threadCounter]+1:])
                fAll.write("T0 ;End of thread\n")
                threadCounter += 1

        ##############################
        ### 5. Add rest of the body lines
        # _ui.messageBox('layerAfterThread:'+str(layerAfterThread)+'\nlen(layerChangeIndexesBody):'+str(len(layerChangeIndexesBody)))
        if layerAfterThread <= len(layerChangeIndexesBody):
            fAll.writelines(fBodyLines[layerChangeIndexesBody[layerAfterThread]:-1])
            
        ##############################
        # 6. Add footer
        fAll.write(';Footer\n')
        fAll.write('M104 S0 ; turn off temperature\n')
        fAll.write('G28 X0  ; home X axis\n')
        fAll.write('M84     ; disable motors\n\n')
        fAll.write('M140 S0 ; set bed temperature\n')
        fAll.write(';End of footer \n')

        fBody.close()
        fAnchor.close()
        fThread.close()
        fAll.close()


    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))



class MyCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # when the command is done, terminate the script
            # this will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
