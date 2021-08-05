#Author-Hyunyoung Kim
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback
import subprocess
import cmath, math
import sys
import inspect
import os

#Use the below three lines if you get error "ModuleNotFoundError: No module named 'numpy'". They may not work on Mac.
import subprocess
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
import numpy as np

script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
script_name = os.path.splitext(os.path.basename(script_path))[0]
script_dir = os.path.dirname(script_path)

sys.path.append(script_dir + "\Modules")
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
_filePath = "C:\Program Files\Slic3r"
_slic3rPath = "C:\Program Files\Slic3r\\"

# Print settings
_layerHeight = 0.2
_bedSizeX = 79        ##TODO Currently set for 79 x 235 mm.
_bedSizeOriginalX = 235
_threadOriginX = -(_bedSizeOriginalX/2 - _bedSizeX/2)
_bedSizeY = 235

# To combine three g-code files
_threadZPoints = [0.0]


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

                fileName = outDir + "/" + comp.name.replace(" ","_" ) + body.name

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
            
            # Get the CommandInputs collection associated with the command.
            _inputs = cmd.commandInputs
            #inputs = cmd.commandInputs
            
            # Connect to command inputs.
            des = adsk.fusion.Design.cast(_app.activeProduct)
            um = des.unitsManager       # TODO. change the unit.

            # Thread selector
            threadInput = _inputs.addSelectionInput('selThread', 'Select Threads', 'Select edges and sketchlines to export as thread')
            #threadInput.addSelectionFilter(adsk.core.SelectionCommandInput.Edges)
            threadInput.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
            threadInput.setSelectionLimits(1)

            # Print body selector
            modelInput = _inputs.addSelectionInput('selBody', 'Select 3D Models', 'Select bodies to 3D print')
            modelInput.addSelectionFilter(adsk.core.SelectionCommandInput.SolidBodies) # Ref https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-03033DE6-AD8E-46B3-B4E6-DADA8D389E4E
            modelInput.setSelectionLimits(1)

            # Anchor body selector
            modelInput = _inputs.addSelectionInput('selAnchor', 'Select Anchors', 'Select bodies to to anchor thread')
            modelInput.addSelectionFilter(adsk.core.SelectionCommandInput.SolidBodies)
            modelInput.setSelectionLimits(0)

            # File path
            filePathInput = _inputs.addStringValueInput('strFilePath', 'File Path', _filePath)

            #Slic3r path
            slic3rPathInput = _inputs.addStringValueInput('strSlic3rPath', 'Slic3r Path', _slic3rPath)

        except:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# #TODO: Remove this class?
# class MyCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
#     def __init__(self):
#         super().__init__()
#     def notify(self, args):
#         try:
#             app = adsk.core.Application.get()
#             design = adsk.fusion.Design.cast(app.activeProduct)
#             if design:
#                 cggroup = design.rootComponent.customGraphicsGroups.add()
#                 for i in range(0, len(_selectedLines)):
#                     if _selectedLines[i].classType() == "adsk::fusion::BRepEdge":
#                         edge = adsk.fusion.BRepEdge.cast(_selectedLines[i]) 
#                         startPoint = edge.startVertex.geometry   # Point3D type
#                         endPoint = edge.endVertex.geometry
#                     else:
#                         edge = adsk.fusion.SketchLine.cast(_selectedLines[i]) # "adsk::fusion::SketchLine"
#                         startPoint = edge.worldGeometry.startPoint
#                         endPoint = edge.worldGeometry.endPoint
                    
#                     #ui.messageBox('(({},{},{}),({},{},{}))'.format(startPoint.x*10, startPoint.y*10, startPoint.z*10, endPoint.x*10, endPoint.y*10, endPoint.z*10))
                    
#         #HK: Not sure what should be done here for bodies. Leave it for now.
                    
#         except:
#             if _ui:
#                 _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))       


def createZeroMatrix(l, r, c):
    mat = []
    for i in range(l):
        layerList = []
        for j in range(r):
            rowList = []
            for k in range(c):
                rowList.append(0)
            layerList.append(rowList)
        mat.append(layerList)
        
    return mat


class MyExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            adsk.core.EventArgs = adsk.core.CommandEventArgs.cast(args)

            selThread = _inputs.itemById('selThread')
            selThread = adsk.core.SelectionCommandInput.cast(selThread)
            for i in range(0, selThread.selectionCount):
                line = adsk.fusion.SketchLine.cast(selThread.selection(i).entity)
                _selectedLines.append(line)

            selBody = _inputs.itemById('selBody')
            selBody = adsk.core.SelectionCommandInput.cast(selBody)
            for i in range(0, selBody.selectionCount):
                body = adsk.fusion.BRepBody.cast(selBody.selection(i).entity)
                _selecedBodies.append(body)

            selAnchor = _inputs.itemById('selAnchor')
            selAnchor = adsk.core.SelectionCommandInput.cast(selAnchor)
            for i in range(0, selAnchor.selectionCount):
                anchor = adsk.fusion.BRepBody.cast(selAnchor.selection(i).entity)
                _selectedAnchors.append(anchor)

            exportThread()
            exportBody()
            exportAnchor()

            combineGCodeFiles()

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def exportThread():
    lines = np.zeros(shape=(len(_selectedLines), 2, 3))
    #lines = createZeroMatrix(len(selectedLines), 2, 3)
    #ui.messageBox(str(lines))
    f = open(_filePath +"\output-thread.txt", "w")
    #TODO: check connectivity and Eulerian trail from (0,0,0)
    for i in range(0, len(_selectedLines)):
        if _selectedLines[i].classType() == "adsk::fusion::BRepEdge":
            edge = adsk.fusion.BRepEdge.cast(_selectedLines[i]) 
            startPoint = edge.startVertex.geometry   # Point3D type
            endPoint = edge.endVertex.geometry
        else:
            edge = adsk.fusion.SketchLine.cast(_selectedLines[i]) # "adsk::fusion::SketchLine"
            startPoint = edge.worldGeometry.startPoint
            endPoint = edge.worldGeometry.endPoint
    
        lines[i][0] = [startPoint.x*10, startPoint.y*10, startPoint.z*10]
        lines[i][1] = [endPoint.x*10, endPoint.y*10, endPoint.z*10]


    ##############################
    ### 1. Order lines from the origin

    tmpIndex = np.where((lines[:,:,0] == _threadOriginX) & (lines[:,:,1] == 0) & (lines[:,:,2] == 0))
    _ui.messageBox(str(tmpIndex))

    # tmpIndex = ((lines[:,:,0] == _threadOriginX) & (lines[:,:,1] == 0) & (lines[:,:,2] == 0)).nonzero()  #TODO: Handle cases where there are more than one origin [_threadOriginX,0,0] or no origin. 

    lines[[tmpIndex[0][0], 0]] = lines[[0, tmpIndex[0][0]]]     # Move origin to the first row
    lines[0, [0, tmpIndex[1][0]]] = lines[0, [tmpIndex[1][0], 0]]          # Move origin to the first column
    _ui.messageBox(str(lines))

    # Sort lines from the origin.
    for i in range(1, len(lines)):
        _ui.messageBox(str(lines[i-1, 1]))
        _ui.messageBox(str(lines[i:]))

        tmpIndex = np.where((lines[i:,:,0] == lines[i-1, 1, 0]) & (lines[i:,:,1] == lines[i-1, 1, 1]) & (lines[i:,:,2] == lines[i-1, 1, 2]))
        #tmpIndex = ((lines[i:,:,0] == lines[i-1, 1, 0]) & (lines[i:,:,1] == lines[i-1, 1, 1]) & (lines[i:,:,2] == lines[i-1, 1, 2])).nonzero()  # Find a line connected to the previous line
        _ui.messageBox(str(tmpIndex))

        if i < len(lines) - 1:
            _ui.messageBox(str(lines[[tmpIndex[0][0], i]]))
            lines[[tmpIndex[0][0], i]] = lines[[i, tmpIndex[0][0]]]     # Move the line to the current row
        lines[i, [0, tmpIndex[1][0]]] = lines[i, [tmpIndex[1][0], 0]]                         # Move the point of the line that is connected to the previous line to the first column

        # TODO: handle exception when the lines are not connected.
    
    f.write(str(lines))
    #ui.messageBox(str(lines))

    #TODO: Select connected lines at once
    #TODO: Check line connectivity

    # Get Z positions of end points of thread. Ignore Z=0
    for line in lines:
        for endPoint in line:
            if endPoint[2] != 0 and endPoint[2] != _threadZPoints[-1]: #TODO: Handle a case then thread goes down.
                _threadZPoints.append(endPoint[2])

    f.write('\n'+str(_threadZPoints))

    ### 2. Conver thread geometry to g-code

    h = 117.5 # Center point of the ring in mm
    r = 100 # Radius of the ring in mm
    stepsPCircle = 142.5
    theta = math.radians(-90)
    
    f.write('\n\nT1 ; change tool to Extruder 2\n')
    f.write('G92 E0 ; set the current filament position to E2=0\n') # Assume 12 o'clock is E2=0

    # 2.a Move bed at Y=0.
    f.write('G0 Y0 ; Move bed to 0\n')

    # 2.b project the position on the ring. If there are anchors on the way, (1) lift the ring up, (2) go to the position (slightly outer than the anchor), (3) go to the position
    for i in range(0, len(lines)):
        startPoint = lines[i][0]
        endPoint = lines[i][1]
        
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
        
        f.write(';Spool points: (({},{}),({},{}))\n'.format(spoolPoint1x, spoolPoint1y, spoolPoint2x, spoolPoint2y))

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

        

        #tTheta = cmath.atan((tSpoolPointy-h)/(tSpoolPointx-h))
        f.write(';Target spool points: ({},{})\n'.format(tSpoolPointx, tSpoolPointy))
        
        # Convert spool xy point to the rotation of the ring
        # Get rotational direction to get to the target spool point


        dTheta = tTheta - theta
        f.write(';Theta, tTheta, dTheta: ({},{},{})\n'.format(math.degrees(theta), math.degrees(tTheta), math.degrees(dTheta)))
        

        #ui.messageBox("dTheta: {}".format(math.degrees(abs(dTheta))))
        temp = round(-1 * dTheta / (2 * cmath.pi) * stepsPCircle, 2)      # -1 is to inverse the angle. + is to rotate the ring clockwise and - is for anticlockwise
        #ui.messageBox("steps: {}".format(temp))
        
        f.write("G1 E{} Z{} F800\n".format(temp, tSpoolPointz))
            
        theta = tTheta


    f.write('T0 ; change back to normal extruder')
    f.close()

    ##############################
    # 3. Export 3D model to g-code using slic3r
    # 3.a Use slic3r, create g-code
    # 3.b Add anchors


def exportBody():
    try:
        product = _app.activeProduct
        design = adsk.fusion.Design.cast(product)
        exportMgr = design.exportManager

        # Export each body to a stl file
        for body in _selecedBodies:
            fileName = _filePath + "/" + body.name

            # create stl exportOptions
            stlExportOptions = exportMgr.createSTLExportOptions(body, fileName)
            stlExportOptions.sendToPrintUtility = False
            stlExportOptions.isBinaryFormat = False
            
            exportMgr.execute(stlExportOptions)

        # Combine the stl files into one file.
        f_all = open(_filePath +"/allBodies.stl", "w")
        f_all.write("solid ASCII\n")

        for body in _selecedBodies:
            f = open(_filePath + "/" + body.name + ".stl", "r")
            count = f.readlines()
            # _ui.messageBox(str(type(count)))
            for i in range(1, len(count)-1):
                f_all.write(count[i])

        f_all.write("endsolid")
        f_all.close()

        result = subprocess.check_output([_slic3rPath + "slic3r-console",
        _filePath + "/allBodies.stl",
        "--first-layer-height", str(_layerHeight),
        "--layer-height",str(_layerHeight),
        "--filament-diameter","1.75",
        "--nozzle-diameter","0.4",
        "--dont-arrange",
        "-o", _filePath + "/output-body.gcode"]) 

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def exportAnchor():
    try:
        product = _app.activeProduct
        design = adsk.fusion.Design.cast(product)
        exportMgr = design.exportManager

        # Export each body to a stl file
        for anchor in _selectedAnchors:
            fileName = _filePath + "/" + anchor.name

            # create stl exportOptions
            stlExportOptions = exportMgr.createSTLExportOptions(anchor, fileName)
            stlExportOptions.sendToPrintUtility = False
            stlExportOptions.isBinaryFormat = False
            
            exportMgr.execute(stlExportOptions)

        # Combine the stl files into one file.
        f_all = open(_filePath +"/allAnchors.stl", "w")
        f_all.write("solid ASCII\n")

        for anchor in _selectedAnchors:
            f = open(_filePath + "/" + anchor.name + ".stl", "r")
            count = f.readlines()
            # _ui.messageBox(str(type(count)))
            for i in range(1, len(count)-1):
                f_all.write(count[i])

        f_all.write("endsolid")
        f_all.close()

        result = subprocess.check_output([_slic3rPath + "slic3r-console",
        _filePath + "/allAnchors.stl",
        "--first-layer-height", str(_layerHeight),
        "--layer-height",str(_layerHeight),
        "--filament-diameter","1.75",
        "--nozzle-diameter","0.4",
        "--dont-arrange",
        "-o", _filePath + "/output-anchor.gcode"]) 

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def combineGCodeFiles():
    try:
        fBody = open(_filePath +"/output-body.gcode", "r")
        fAnchor = open(_filePath +"/output-anchor.gcode", "r")
        fAll = open(_filePath +"/output-all.gcode", "w")

        linesBody = fBody.readlines()
        linesAnchor = fAnchor.readlines()

        #TODO: Start from here.


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


# class MyPreSelectHandler(adsk.core.SelectionEventHandler):
#     def __init__(self):
#         super().__init__()
#     def notify(self, args):
#         try:
#             selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity)
#             if selectedEdge:
#                 args.additionalEntities = selectedEdge.tangentiallyConnectedEdges        
#         except:
#             if _ui:
#                 _ui.messageBox('Failed:\n{}'.format(traceback.format_exc())) 
