import adsk.core, adsk.fusion

class Thread:
	def __init__(self):
		self.app = adsk.core.Application.get()
		self.ui  = self.app.userInterface
