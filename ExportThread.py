#Author-Hyunyoung Kim
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback
import cmath, math
import sys

#import subprocess
#subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
#import numpy as np

import inspect
import os
import sys

script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
script_name = os.path.splitext(os.path.basename(script_path))[0]
script_dir = os.path.dirname(script_path)

sys.path.append(script_dir + "\Modules")
try:
    import numpy as np
finally:
    del sys.path[-1]



app = adsk.core.Application.cast(None)
ui = adsk.core.UserInterface.cast(None)
handlers = []
selectedLines = []

pathGcode = os.path.abspath(__file__) + "threadCoordinates.txt"
pathSlic3r = "C:\Program Files\Slic3r-1.3.0.64bit\Slic3r-console"


def run(context):
    global app, ui
    ui = None
    try:
        app= adsk.core.Application.get()
        ui= app.userInterface
        des = adsk.fusion.Design.cast(app.activeProduct)
        root = des.rootComponent
        
        myCmdDef = ui.commandDefinitions.itemById('thread_selector')
        if myCmdDef is None:
            myCmdDef = ui.commandDefinitions.addButtonDefinition('thread_selector', 'Select Thread Paths', '', '')

        # Connect to the command created event.
        onCommandCreated = MyCommandCreatedHandler()
        myCmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)

        # Execute the command.
        myCmdDef.execute()

        # prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)

        ##########

        # #selection = _ui.selectEntity('Select a line', 'Edges,SketchCurves') # Select an edge from BRepEdge or Sketch. For multiple selections, look at "addSelection" http://help.autodesk.com/view/fusion360/ENU/?guid=GUID-568db63a-0f28-4307-9e02-e29f54820db1
        # selection = _ui.selectEntity('Select a line', 'Edges')
        # lines = adsk.fusion.BRepEdge.cast(selection.entity) # TODO. handle sketch lines as well.

        # # TODO. Enable multiple selections <- later
        # # TODO. Somehow export the edge info. that means I need to look at the entity
        # exportEdgets(root, lines)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command
            cmd.isExecutedWhenPreEmpted = False
            inputs = cmd.commandInputs
            
            selectInput = inputs.addSelectionInput('SelectionThreadPaths', 'Edges,SketchCurves', 'Please select edges')
            selectInput.addSelectionFilter(adsk.core.SelectionCommandInput.Edges)
            selectInput.addSelectionFilter(adsk.core.SelectionCommandInput.SketchCurves)
            selectInput.setSelectionLimits(1)
            
            # Connect to the command related events.
            onExecutePreview = MyCommandExecutePreviewHandler()
            cmd.executePreview.add(onExecutePreview)
            handlers.append(onExecutePreview)        

            # Connect to command excute handler. 
            onExecute = MyExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

            onDestroy = MyCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            handlers.append(onDestroy)  
            
            onPreSelect = MyPreSelectHandler()
            cmd.preSelect.add(onPreSelect)
            handlers.append(onPreSelect)
            
            # onPreSelectMouseMove = MyPreSelectMouseMoveHandler()
            # cmd.preSelectMouseMove.add(onPreSelectMouseMove)
            # handlers.append(onPreSelectMouseMove)

            # onPreSelectEnd = MyPreSelectEndHandler()
            # cmd.preSelectEnd.add(onPreSelectEnd)
            # handlers.append(onPreSelectEnd)

            onSelect = MySelectHandler()
            cmd.select.add(onSelect)
            handlers.append(onSelect) 
            
            onUnSelect = MyUnSelectHandler()
            cmd.unselect.add(onUnSelect)            
            handlers.append(onUnSelect) 
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MyCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                cggroup = design.rootComponent.customGraphicsGroups.add()
                for i in range(0, len(selectedLines)):
                    if selectedLines[i].classType() == "adsk::fusion::BRepEdge":
                        edge = adsk.fusion.BRepEdge.cast(selectedLines[i]) 
                        startPoint = edge.startVertex.geometry   # Point3D type
                        endPoint = edge.endVertex.geometry
                    else:
                        edge = adsk.fusion.SketchLine.cast(selectedLines[i]) # "adsk::fusion::SketchLine"
                        startPoint = edge.worldGeometry.startPoint
                        endPoint = edge.worldGeometry.endPoint
                    
                    #ui.messageBox('(({},{},{}),({},{},{}))'.format(startPoint.x*10, startPoint.y*10, startPoint.z*10, endPoint.x*10, endPoint.y*10, endPoint.z*10))
                    
                    
                    
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))       

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
        lines = np.zeros(shape=(len(selectedLines), 2, 3))
        #lines = createZeroMatrix(len(selectedLines), 2, 3)
        #ui.messageBox(str(lines))
        try:
            f = open(pathGcode, "w")
            #TODO: check connectivity and Eulerian trail from (0,0,0)
            for i in range(0, len(selectedLines)):
                if selectedLines[i].classType() == "adsk::fusion::BRepEdge":
                    edge = adsk.fusion.BRepEdge.cast(selectedLines[i]) 
                    startPoint = edge.startVertex.geometry   # Point3D type
                    endPoint = edge.endVertex.geometry
                else:
                    edge = adsk.fusion.SketchLine.cast(selectedLines[i]) # "adsk::fusion::SketchLine"
                    startPoint = edge.worldGeometry.startPoint
                    endPoint = edge.worldGeometry.endPoint
                    
                #f.write('(({},{},{}),({},{},{}))\n'.format(startPoint.x*10, startPoint.y*10, startPoint.z*10, endPoint.x*10, endPoint.y*10, endPoint.z*10))
            
                lines[i][0] = [startPoint.x*10, startPoint.y*10, startPoint.z*10]
                lines[i][1] = [endPoint.x*10, endPoint.y*10, endPoint.z*10]
                #f.write('(({},{},{}),({},{},{}))\n'.format(lines[i][0][0], lines[i][0][1], lines[i][0][2], lines[i][1][0], lines[i][1][1], lines[i][1][2]))


            # Order lines from the origin

            tmpIndex = ((lines[:,:,0] == 0) & (lines[:,:,1] == 0) & (lines[:,:,2] == 0)).nonzero()  #TODO: Handle cases where there are more than one [0,0,0] or no [0,0,0]. tmpIndex should be 1d array, e.g., [1,1]
            #tmpIndex = np.where((lines == (0,0,0)).all(axis=2).nonzero())
            # ui.messageBox("tmpIndex: (0,0,0)\n"+str(lines == (0,0,0)))
            # ui.messageBox("tmpIndex: nonzero\n"+str((lines == (0,0,0)).all(axis=2).nonzero()))
            # ui.messageBox("tmpIndex: where\n"+str(np.where((lines[:,:,0] == 0) & (lines[:,:,1] == 0) & (lines[:,:,2] == 0))[0]))
            # ui.messageBox(gcodePath)
            # ui.messageBox("lines: "+str(lines))
            # ui.messageBox("tmpIndex: "+str(tmpIndex))
            lines[[tmpIndex[0][0], 0]] = lines[[0, tmpIndex[0][0]]]     # Move [0,0,0] to the first row
            lines[0, [0, tmpIndex[1][0]]] = lines[0, [tmpIndex[1][0], 0]]          # Move [0,0,0] to the first column
            #ui.messageBox(str(lines))
            for i in range(1, len(lines)):
                tmpIndex = ((lines[i:,:,0] == lines[i-1, 1, 0]) & (lines[i:,:,1] == lines[i-1, 1, 1]) & (lines[i:,:,2] == lines[i-1, 1, 2])).nonzero()  # Find a line connected to the previous line
                #ui.messageBox("Iteration {}:\n{}".format(i, str(tmpIndex)))

                if i < len(lines) - 1:
                    ui.messageBox(str(lines[[tmpIndex[0][0], i]]))
                    lines[[tmpIndex[0][0], i]] = lines[[i, tmpIndex[0][0]]]     # Move the line to the current row
                lines[i, [0, tmpIndex[1][0]]] = lines[i, [tmpIndex[1][0], 0]]                         # Move the point of the line that is connected to the previous line to the first column
                #ui.messageBox("Iteration {}:\n{}".format(i, str(lines)))
                # TODO: handle exception when the lines are not connected.
            
            f.write(str(lines))
            #ui.messageBox(str(lines))

            #TODO: convert geometry to g-code
            #TODO: Use slic3r, export the body as well.
            #TODO: Select connected lines at once
            #TODO: Check line connectivity
            #TODO: Order lines from (0, 0, 0)

            ##############################
            # 1. Find the nearest point, draw a 3D line from (0,0,0) to that. https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-98e163be-fd07-11e4-9c39-3417ebd3d5be
            # 1.a Find the nearest point to the origin point
            # 1.b Create a horizontal plane at the point
            # 1.c Create a sketch on the plane
            # 1.d Add a line by using addByTwoPoints (e.g., lines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(3, 1, 0)))

            ##############################
            # 2. Conver thread geometry to g-code

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





        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# def checkEulerianPath():
#     try:
#         # 1. Check connectivity
#         start_node = selectedLines[0]
#         color = {v: 'white' for v in selectedLines}
#         color[start_node] = 'gray'
#         S = [start_node]
#         while len(S) != 0:
#             u = S.pop()
#             for v in G[u]:
#                 if color[v] == 'white':
#                     color[v] = 'gray'
#                     S.append(v)
# 			color[u] = 'black'
#         return list(color.values()).count('black') == len(selectedLines)

#     except:
#         ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MyCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # when the command is done, terminate the script
            # this will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                

class MyPreSelectHandler(adsk.core.SelectionEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity)
            if selectedEdge:
                args.additionalEntities = selectedEdge.tangentiallyConnectedEdges        
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc())) 
                

# class MyPreSelectMouseMoveHandler(adsk.core.SelectionEventHandler):
#     def __init__(self):
#         super().__init__()
#     def notify(self, args):
#         try:
#             app = adsk.core.Application.get()
#             design = adsk.fusion.Design.cast(app.activeProduct)
#             selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
#             if design and selectedEdge:
#                 group = design.rootComponent.customGraphicsGroups.add()
#                 group.id = str(selectedEdge.tempId)
#                 cgcurve = group.addCurve(selectedEdge.geometry)
#                 cgcurve.color = adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(255,0,0,255))
#                 cgcurve.weight = 10      
#         except:
#             if ui:
#                 ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                

# class MyPreSelectEndHandler(adsk.core.SelectionEventHandler):
#     def __init__(self):
#         super().__init__()
#     def notify(self, args):
#         try:
#             app = adsk.core.Application.get()
#             design = adsk.fusion.Design.cast(app.activeProduct)
#             selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
#             if design and selectedEdge:
#                 for group in design.rootComponent.customGraphicsGroups:
#                     if group.id == str(selectedEdge.tempId):
#                         group.deleteMe()
#                         break       
#         except:
#             if ui:
#                 ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                

class MySelectHandler(adsk.core.SelectionEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            #ui.messageBox(args.selection.entity.classType())
            if args.selection.entity.classType() == "adsk::fusion::BRepEdge":
                selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
            else:
                selectedEdge = adsk.fusion.SketchLine.cast(args.selection.entity) 
            if selectedEdge:
                selectedLines.append(selectedEdge)

            # selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
            # if selectedEdge:
            #     selectedLines.append(selectedEdge)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                

class MyUnSelectHandler(adsk.core.SelectionEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            selectedEdge = adsk.fusion.BRepEdge.cast(args.selection.entity) 
            if selectedEdge:
                selectedLines.append(selectedEdge)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# #TODO: make the __init__ work
# class ExportEdges(adsk.fusion.Design.rootComponent):
#     def __init__(self):
#         root = args

#     def print(self, args):
#         try:
#             # Get the geometry of the edges
#             # TODO: if the edge is from BRepEdge
#             startPoint = args.startVertex.geometry   # Point3D type
#             endPoint = args.endVertex.geometry

#             #ui.messageBox('Point:\n({}, {}, {})\n({}, {}, {})'.format(startPoint.x, startPoint.y, startPoint.z, endPoint.x, endPoint.y, endPoint.z))
#         except:
#             ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
        
